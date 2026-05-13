"""
RAG 知识库 Service

封装 RAG 完整业务逻辑：文件解析 -> 文本分块 -> 向量化 -> Repository 存储。
向量化逻辑位于本层，Repository 层只负责纯粹的向量数据 CRUD。
"""
from __future__ import annotations

import logging
from datetime import datetime
from functools import lru_cache

from pathlib import Path

from app.core.config import settings
from app.repositories.milvus_store import get_knowledge_repository
from app.tools.chunking import make_doc_id, split_text
from app.tools.file_parser import parse_file, parse_bytes

logger = logging.getLogger(__name__)

_repo = None


def _get_repo():
    """懒加载 KnowledgeRepository，避免模块导入时初始化外部依赖。"""
    global _repo
    if _repo is None:
        _repo = get_knowledge_repository()
    return _repo


# ------------------------------------------------------------------ #
# 文件解析（含 PDF 缓存复用）
# ------------------------------------------------------------------ #
def _get_text_and_filename(file_path: str) -> tuple[str, str]:
    """
    获取文件文本和文件名。
    PDF 文件优先复用 parse_pdf 工具产生的缓存（workspace/parsed/），
    避免重复解析；解析后也会写入缓存，供 parse_pdf 复用。
    """
    path = Path(file_path).resolve()

    # PDF 优先读缓存
    if path.suffix.lower() == ".pdf":
        from app.tools.pdf import get_parsed_pdf_path
        cache_path = get_parsed_pdf_path(str(path))
        if cache_path.exists():
            logger.info("[ingest_document] 复用 parse_pdf 缓存: %s", cache_path)
            return cache_path.read_text(encoding="utf-8"), path.name

    # 无缓存则解析
    result = parse_file(file_path)
    if not result.success:
        raise ValueError(f"文件解析失败：{result.error}")

    # PDF 写入缓存，供 parse_pdf 复用
    if path.suffix.lower() == ".pdf":
        from app.tools.pdf import get_parsed_pdf_path
        cache_path = get_parsed_pdf_path(str(path))
        try:
            cache_path.write_text(result.text, encoding="utf-8")
            logger.info("[ingest_document] PDF 解析结果已缓存: %s", cache_path)
        except Exception as e:
            logger.warning("[ingest_document] 缓存写入失败: %s", e)

    return result.text, result.filename


# ------------------------------------------------------------------ #
# Embedding（Service 层职责）
# ------------------------------------------------------------------ #
@lru_cache(maxsize=1)
def _get_embedder():
    """构建并缓存 LangChain embedding 实例。"""
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model=settings.MEMORY_EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def _embed(texts: list[str]) -> list[list[float]]:
    """对文本列表向量化，返回 float 向量列表。"""
    return _get_embedder().embed_documents(texts)


# ------------------------------------------------------------------ #
# 业务接口
# ------------------------------------------------------------------ #
def ingest_document(file_path: str, user_id: str) -> str:
    """
    将本地文件解析、分块并持久化到 RAG 知识库。
    完整流程：文件解析（PDF 优先复用 parse_pdf 缓存）-> 文本分块 -> 向量化 -> 写入 Milvus RAG collection。
    同一用户上传同名文件会先删除旧数据再重新入库（幂等）。
    """
    try:
        text, filename = _get_text_and_filename(file_path)

        doc_id = make_doc_id(filename, user_id)
        _get_repo().delete_by_doc_id(doc_id, user_id)  # 幂等：先清除旧数据
        chunks = split_text(text=text, filename=filename,
                            user_id=user_id, doc_id=doc_id)
        if not chunks:
            return f"文件内容为空，无法入库：{filename}"

        vectors = _embed([c.text for c in chunks])
        count = _get_repo().insert(chunks, vectors)
        return f"文件「{filename}」已成功入库，共 {count} 个片段，doc_id: {doc_id}"

    except Exception as e:
        logger.error("[ingest_document] 失败: %s", e)
        return f"文件入库失败：{e}"


def ingest_bytes(data: bytes, filename: str, user_id: str) -> str:
    """
    从字节数据入库（适用于上传场景，无需先落盘到固定路径）。
    """
    try:
        result = parse_bytes(data, filename)
        if not result.success:
            return f"文件解析失败：{result.error}"

        doc_id = make_doc_id(result.filename, user_id)
        _get_repo().delete_by_doc_id(doc_id, user_id)

        chunks = split_text(text=result.text, filename=result.filename,
                            user_id=user_id, doc_id=doc_id)
        if not chunks:
            return f"文件内容为空，无法入库：{result.filename}"

        vectors = _embed([c.text for c in chunks])
        count = _get_repo().insert(chunks, vectors)
        return f"文件「{result.filename}」已成功入库，共 {count} 个片段，doc_id: {doc_id}"

    except Exception as e:
        logger.error("[ingest_bytes] 失败: %s", e)
        return f"文件入库失败：{e}"


def search_knowledge(query: str, user_id: str, top_k: int = 5) -> str:
    """
    从 RAG 知识库中语义检索与查询最相关的文档片段。
    """
    try:
        query_vec = _embed([query])[0]
        hits = _get_repo().search(query_vec, user_id=user_id, top_k=top_k)
        if not hits:
            return "知识库中未找到相关内容。"

        lines = [
            f"[{i}] 来源：{h['source']}（片段 {h['chunk_index']}）\n{h['text']}"
            for i, h in enumerate(hits, 1)
        ]
        return "\n\n".join(lines)

    except Exception as e:
        logger.error("[search_knowledge] 失败: %s", e)
        return f"知识库检索失败：{e}"


def list_documents(user_id: str) -> str:
    """
    列出用户已入库的所有文档。
    """
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
    """
    从知识库中删除指定文档的所有片段。
    """
    try:
        count = _get_repo().delete_by_doc_id(doc_id, user_id)
        if count == 0:
            return f"未找到 doc_id={doc_id} 的文档，或该文档不属于当前用户。"
        return f"已删除文档 doc_id={doc_id}，共清除 {count} 个片段。"

    except Exception as e:
        logger.error("[delete_document] 失败: %s", e)
        return f"删除文档失败：{e}"
