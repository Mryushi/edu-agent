"""
RAG 知识库 Service

封装 RAG 完整业务逻辑：文件解析 → 文本分块 → 向量化 → Repository 存储 → 检索。
所有增量入库决策（new / modified / unchanged / stale）都集中在本层，
Repository 只接收明确的 CRUD 命令；Repository 不再做隐式过滤。

检索链路：query → qwen3 dense embedding + 原文 → Milvus hybrid_search
        (dense ANN + BM25 sparse, RRF 融合) → 关联记忆。
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from app.core.config import settings
from app.core.llms import rag_dense_embedder
from app.repositories.milvus_store import get_knowledge_repository
from app.tools.chunking import Chunk, make_doc_id, split_text
from app.tools.file_parser import parse_bytes

logger = logging.getLogger(__name__)

_repo = None
_repo_lock = threading.Lock()


def _get_repo():
    """懒加载 KnowledgeRepository，避免模块导入时初始化外部依赖（线程安全）。"""
    global _repo
    if _repo is None:
        with _repo_lock:
            if _repo is None:
                _repo = get_knowledge_repository()
    return _repo


# ------------------------------------------------------------------ #
# Embedding（委托给 llms.py 统一管理）
# ------------------------------------------------------------------ #
def _embed(texts: list[str]) -> list[list[float]]:
    """对文本列表做稠密向量化。"""
    return rag_dense_embedder.embed_documents(texts)


# ------------------------------------------------------------------ #
# 文件解析（含缓存复用）
# ------------------------------------------------------------------ #
def _get_text_and_filename(file_path: str) -> tuple[str, str]:
    """获取文件文本和文件名。

    优先复用基于 bytes hash 的解析缓存（workspace/parsed/），避免重复解析；
    解析后也会写入缓存，供后续复用。
    """
    from app.tools.file_parser import parse_file_with_cache

    result = parse_file_with_cache(file_path)
    if not result.success:
        raise ValueError(f"文件解析失败：{result.error}")

    return result.text, result.filename


# ------------------------------------------------------------------ #
# 增量入库（决策 / 校验 / 执行 分离）
# ------------------------------------------------------------------ #

class IngestionRejectedError(ValueError):
    """完整性校验拒绝入库时抛出"""
    pass


@dataclass
class IngestionPlan:
    """增量入库执行计划"""
    chunks: list[Chunk]
    filename: str
    doc_id: str
    user_id: str
    replace: bool
    new_chunks: list[Chunk] = field(default_factory=list)
    modified_chunks: list[Chunk] = field(default_factory=list)
    unchanged_count: int = 0
    stale_ids: list[str] = field(default_factory=list)
    existing_count: int = 0

    @property
    def shrink_ratio(self) -> float:
        return len(self.chunks) / max(self.existing_count, 1)

    @property
    def chunks_to_embed(self) -> list[Chunk]:
        return self.new_chunks + self.modified_chunks

    @property
    def ids_to_delete(self) -> list[str]:
        return [c.chunk_id for c in self.modified_chunks] + self.stale_ids


def _plan_ingestion(
    chunks: list[Chunk],
    filename: str,
    doc_id: str,
    user_id: str,
    *,
    replace: bool = True,
) -> IngestionPlan:
    """纯决策：查询已有记录，分类 chunks，计算 stale_ids。零副作用。

    Returns:
        IngestionPlan，包含 new/modified/unchanged 分类和 stale_ids 列表。
    """
    repo = _get_repo()
    existing_hashes = repo.get_hashes_by_doc_id(doc_id, user_id)
    current_ids = {c.chunk_id for c in chunks}

    new_chunks: list[Chunk] = []
    modified_chunks: list[Chunk] = []
    unchanged_count = 0
    for c in chunks:
        old_hash = existing_hashes.get(c.chunk_id)
        if old_hash is None:
            new_chunks.append(c)
        elif old_hash != c.content_hash:
            modified_chunks.append(c)
        else:
            unchanged_count += 1

    stale_ids = [cid for cid in existing_hashes if cid not in current_ids] if replace else []

    return IngestionPlan(
        chunks=chunks,
        filename=filename,
        doc_id=doc_id,
        user_id=user_id,
        replace=replace,
        new_chunks=new_chunks,
        modified_chunks=modified_chunks,
        unchanged_count=unchanged_count,
        stale_ids=stale_ids,
        existing_count=len(existing_hashes),
    )


def _validate_plan(plan: IngestionPlan, *, force: bool = False) -> None:
    """校验入库计划。不通过时抛出 IngestionRejectedError。零副作用。

    当前规则：
      - replace=True 且已有记录时，新片段数 < 旧版本 50% 则拒绝。
      - force=True 时跳过校验，允许强制覆盖。
    """
    if force:
        return
    if plan.replace and plan.existing_count > 0:
        if plan.shrink_ratio < 0.5:
            raise IngestionRejectedError(
                f"入库被拒绝：新文件片段数（{len(plan.chunks)}）仅为旧版本（{plan.existing_count}）的"
                f"{plan.shrink_ratio:.0%}，疑似不完整上传。"
                f"如需仅更新传入的部分而不删除旧内容，请使用 replace=False 重新入库。"
            )


def _execute_ingestion(plan: IngestionPlan) -> tuple[int, int]:
    """纯执行：删除旧记录、embedding、插入新记录。

    Args:
        plan: 已通过校验的 IngestionPlan。

    Returns:
        (deleted_count, embed_ms)
    """
    repo = _get_repo()

    ids_to_delete = plan.ids_to_delete
    deleted = repo.delete_chunks_by_ids(ids_to_delete, plan.user_id) if ids_to_delete else 0

    chunks_to_embed = plan.chunks_to_embed
    if chunks_to_embed:
        t0 = time.perf_counter()
        vectors = _embed([c.text for c in chunks_to_embed])
        embed_ms = int((time.perf_counter() - t0) * 1000)
        repo.insert_chunks(chunks_to_embed, vectors)
    else:
        embed_ms = 0

    return deleted, embed_ms


def _format_ingestion_result(plan: IngestionPlan) -> str:
    """将执行结果格式化为用户可读字符串。零副作用。"""
    parts: list[str] = []
    if plan.new_chunks:
        parts.append(f"新增 {len(plan.new_chunks)} 个片段")
    if plan.modified_chunks:
        parts.append(f"更新 {len(plan.modified_chunks)} 个片段")
    if plan.unchanged_count:
        parts.append(f"保留 {plan.unchanged_count} 个未变化片段")
    if plan.stale_ids:
        parts.append(f"删除 {len(plan.stale_ids)} 个过期片段")
    if not parts:
        parts.append("无需变更")

    return f"文件「{plan.filename}」已入库。{'，'.join(parts)}，doc_id={plan.doc_id}"


def _ingest_chunks(
    chunks: list[Chunk],
    filename: str,
    doc_id: str,
    user_id: str,
    *,
    replace: bool = True,
    force: bool = False,
) -> str:
    """执行增量入库流水线：决策 → 校验 → 执行 → 格式化。

    对外的行为与拆分前完全一致；内部已将决策、校验、执行分离，
    便于单独测试和预校验。
    """
    try:
        plan = _plan_ingestion(chunks, filename, doc_id, user_id, replace=replace)
    except Exception as e:
        logger.error(
            "[_ingest_chunks] 查询已有记录失败 file=%s doc_id=%s: %s",
            filename, doc_id, e,
        )
        return f"入库失败：无法查询已有记录（{e}），请检查 Milvus 连接状态后重试。"

    try:
        _validate_plan(plan, force=force)
    except IngestionRejectedError as e:
        return str(e)

    deleted, embed_ms = _execute_ingestion(plan)

    logger.info(
        "[ingest_document] file=%s doc_id=%s replace=%s total=%d new=%d modified=%d "
        "unchanged=%d stale=%d embedded=%d deleted=%d embed_ms=%d",
        filename, doc_id, replace, len(chunks), len(plan.new_chunks), len(plan.modified_chunks),
        plan.unchanged_count, len(plan.stale_ids), len(plan.chunks_to_embed), deleted, embed_ms,
    )

    return _format_ingestion_result(plan)


# ------------------------------------------------------------------ #
# 业务接口
# ------------------------------------------------------------------ #
def ingest_document(
    file_path: str, user_id: str, *, replace: bool = True, force: bool = False
) -> str:
    """将本地文件解析、分块并增量入库到 RAG 知识库。

    增量语义：相同内容不会重复 embedding，修改内容会替换旧记录。
    默认 replace=True 时会清理旧文件中不存在的 chunk（完整替换）；
    replace=False 时只更新传入的部分，保留旧文件中未被覆盖的 chunk。

    Args:
        force: 为 True 时跳过 shrink_ratio 完整性校验，允许强制覆盖。
    """
    try:
        text, filename = _get_text_and_filename(file_path)
        doc_id = make_doc_id(filename, user_id)
        chunks = split_text(text=text, filename=filename, user_id=user_id, doc_id=doc_id)
        if not chunks:
            return f"文件内容为空，无法入库：{filename}"
        return _ingest_chunks(chunks, filename, doc_id, user_id, replace=replace, force=force)
    except Exception as e:
        logger.error("[ingest_document] 失败: %s", e)
        return f"文件入库失败：{e}"


def ingest_bytes(
    data: bytes, filename: str, user_id: str, *, replace: bool = True, force: bool = False
) -> str:
    """从字节数据增量入库（适用于上传场景，无需先落盘到固定路径）。

    replace 参数语义同 ingest_document。
    """
    try:
        result = parse_bytes(data, filename)
        if not result.success:
            return f"文件解析失败：{result.error}"

        doc_id = make_doc_id(result.filename, user_id)
        chunks = split_text(
            text=result.text, filename=result.filename,
            user_id=user_id, doc_id=doc_id,
        )
        if not chunks:
            return f"文件内容为空，无法入库：{result.filename}"
        return _ingest_chunks(
            chunks, result.filename, doc_id, user_id, replace=replace, force=force
        )
    except Exception as e:
        logger.error("[ingest_bytes] 失败: %s", e)
        return f"文件入库失败：{e}"


def search_knowledge(query: str, user_id: str, top_k: int | None = None) -> str:
    """从 RAG 知识库中混合检索与查询最相关的文档片段。

    检索链路：query → qwen3 dense embedding + 原文 → Milvus hybrid_search
            (dense ANN + BM25 sparse, RRF 融合) → 命中文档关联记忆。
    """
    try:
        _top_k = top_k or settings.RAG_TOP_K
        fetch_k = max(settings.RAG_HYBRID_FETCH_K, _top_k * 2)

        t0 = time.perf_counter()
        dense_vec = _embed([query])[0]
        hits, hybrid_success = _get_repo().hybrid_search(
            dense_vector=dense_vec,
            query_text=query,
            user_id=user_id,
            top_k=_top_k,
            fetch_k=fetch_k,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        logger.info(
            "[search_knowledge] user=%s top_k=%d fetch_k=%d hybrid_success=%s hits=%d cost_ms=%d query=%r",
            user_id, _top_k, fetch_k, hybrid_success, len(hits), elapsed_ms, query,
        )

        if not hits:
            return "知识库中未找到相关内容。"

        lines = []
        for i, h in enumerate(hits, 1):
            section = f" [{h['section_path']}]" if h.get("section_path") else ""
            lines.append(
                f"[{i}] 来源：{h['source']}（片段 {h['chunk_index']}）{section}\n{h['text']}"
            )
        result = "\n\n".join(lines)

        # 附带命中文档的关联长期记忆（限制输出长度，避免淹没正文）
        memory_section = _build_memory_appendix(user_id, hits)
        if memory_section:
            result += "\n\n" + memory_section
        if not hybrid_success:
            result += "\n\n[提示] hybrid 检索失败，已降级为 dense-only，结果可能不包含关键词召回。"
        return result

    except Exception as e:
        logger.error("[search_knowledge] 失败: %s", e)
        return f"知识库检索失败：{e}"


_MEMORY_APPENDIX_MAX_DOCS = 3
_MEMORY_APPENDIX_MAX_LINES_PER_DOC = 3


def _build_memory_appendix(user_id: str, hits: list[dict]) -> str:
    """为检索命中的文档附带其关联长期记忆，并限制总输出量。"""
    from app.services.memory_service import list_memories_by_doc

    seen: list[tuple[str, str]] = []
    for h in hits:
        key = (h["doc_id"], h["source"])
        if key not in seen:
            seen.append(key)
        if len(seen) >= _MEMORY_APPENDIX_MAX_DOCS:
            break

    sections: list[str] = []
    for doc_id, source in seen:
        memories = list_memories_by_doc(user_id, doc_id)
        if not memories or "暂无关联记忆" in memories or "获取文档关联记忆失败" in memories:
            continue
        memory_lines = memories.splitlines()[:_MEMORY_APPENDIX_MAX_LINES_PER_DOC]
        sections.append(f"### 关联记忆（文档: {source}）\n" + "\n".join(memory_lines))

    return "\n\n".join(sections)


def list_documents(user_id: str) -> str:
    """列出用户已入库的所有文档。"""
    try:
        docs = _get_repo().list_by_user_id(user_id)
        if not docs:
            return "知识库中暂无文档。"

        lines = []
        for i, d in enumerate(docs, 1):
            ts = datetime.fromtimestamp(d["created_at"]).strftime("%Y-%m-%d %H:%M")
            lines.append(
                f"{i}. 「{d['source']}」 {d['chunk_count']} 个片段  入库: {ts}  doc_id: {d['doc_id']}"
            )
        return "\n".join(lines)

    except Exception as e:
        logger.error("[list_documents] 失败: %s", e)
        return f"获取文档列表失败：{e}"


def delete_document(doc_id: str, user_id: str) -> str:
    """从知识库中删除指定文档的所有片段。"""
    try:
        count = _get_repo().delete_document(doc_id, user_id)
        if count == 0:
            return f"未找到 doc_id={doc_id} 的文档，或该文档不属于当前用户。"
        return f"已删除文档 doc_id={doc_id}，共清除 {count} 个片段。"

    except Exception as e:
        logger.error("[delete_document] 失败: %s", e)
        return f"删除文档失败：{e}"
