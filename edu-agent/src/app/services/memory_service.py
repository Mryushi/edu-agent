"""
mem0 + Milvus 长期记忆 Service

封装记忆管理业务逻辑：保存、检索、列出用户的长期记忆。
底层依赖 app.repositories.mem0_store 提供的 MemoryRepository。
"""
import logging
import threading
from typing import Any, List, Optional

from app.repositories.mem0_store import get_memory_repository

logger = logging.getLogger(__name__)

_ALLOWED_CATEGORIES = {"preference", "progress", "fact", "goal"}

_mem = None
_mem_lock = threading.Lock()


def _get_mem():
    """懒加载 MemoryRepository，避免模块导入时初始化外部依赖（线程安全）。"""
    global _mem
    if _mem is None:
        with _mem_lock:
            if _mem is None:
                _mem = get_memory_repository()
    return _mem


# ------------------------------------------------------------------ #
# 内部辅助
# ------------------------------------------------------------------ #
def _format_add_results(results: List[dict]) -> str:
    """格式化多次 mem0 add() 的返回结果为可读字符串。"""
    total_added = 0
    total_updated = 0
    total_skipped = 0
    memories_added = []
    memories_updated = []
    skipped_events = []
    for result in results:
        for r in result.get("results", []):
            event = r.get("event", "UNKNOWN")
            if event == "ADD":
                total_added += 1
                memories_added.append(r.get("memory", ""))
            elif event == "UPDATE":
                total_updated += 1
                memories_updated.append(r.get("memory", ""))
            else:
                total_skipped += 1
                skipped_events.append(event)
                logger.info(
                    "[save_memory] mem0 事件=%s memory=%s existing_memory=%s",
                    event, r.get("memory", ""), r.get("existing_memory", ""),
                )
    parts = []
    if total_added:
        parts.append(f"已保存 {total_added} 条：{'; '.join(memories_added)}")
    if total_updated:
        parts.append(f"已更新 {total_updated} 条：{'; '.join(memories_updated)}")
    if total_skipped:
        parts.append(f"跳过 {total_skipped} 条（事件：{'、'.join(set(skipped_events))}）")
    return "、".join(parts) if parts else "记忆已处理（无新增/更新）"


def _normalize_fact(fact: Any) -> tuple[str, Optional[str]]:
    """从 Pydantic model 或 dict 提取 user_quote / category。"""
    if isinstance(fact, dict):
        user_quote = (fact.get("user_quote") or "").strip()
        category = fact.get("category")
    else:
        user_quote = (getattr(fact, "user_quote", "") or "").strip()
        category = getattr(fact, "category", None)
    if category is not None:
        category = str(category).strip().lower() or None
        if category and category not in _ALLOWED_CATEGORIES:
            logger.warning(
                "[save_memory] 非法 category=%r，已丢弃；允许值：%s",
                category, sorted(_ALLOWED_CATEGORIES),
            )
            category = None
    return user_quote, category


# ------------------------------------------------------------------ #
# 底层函数（返回原始数据，供上层函数复用）
# ------------------------------------------------------------------ #
def search_memories_raw(
    query: str,
    user_id: str,
    top_k: int = 5,
    only_with_doc_id: bool = False
) -> List[dict]:
    """
    根据查询检索记忆的底层函数，返回原始结构化数据。

    Args:
        query: 检索查询
        user_id: 用户唯一标识
        top_k: 返回记忆数量
        only_with_doc_id: 是否只返回有 doc_id 的记忆（用于 RAG 检索）

    Returns:
        结构化记忆列表，包含 id, memory, metadata, score 等字段
    """
    try:
        results = _get_mem().search(
            query=query,
            filters={"user_id": user_id},
            top_k=top_k
        )
        memories = results.get("results", [])

        if only_with_doc_id:
            return [
                m for m in memories
                if m.get("metadata", {}).get("doc_id")
            ]

        return memories

    except Exception as e:
        logger.error("[search_memories_raw] 失败: %s", e)
        return []


# ------------------------------------------------------------------ #
# 业务接口
# ------------------------------------------------------------------ #
def save_memory(
    user_id: str,
    facts: List[Any],
    conversation_context: Optional[str] = None,
    related_doc_id: Optional[str] = None,
    related_doc_source: Optional[str] = None,
) -> str:
    """
    将结构化记忆事实批量保存到用户的长期记忆中。

    跳过 user_quote 为空的条目，非法 category 会被丢弃并在日志中提示。
    保存失败时返回明确原因，便于上层判断是否需要重试。
    """
    if not facts:
        return "未收到任何记忆事实，已跳过。"

    metadata_base: dict[str, Any] = {}
    if related_doc_id:
        metadata_base["doc_id"] = related_doc_id
    if related_doc_source:
        metadata_base["source"] = related_doc_source

    results: list[dict] = []
    skipped_empty = 0
    failed: list[str] = []

    for fact in facts:
        user_quote, category = _normalize_fact(fact)
        if not user_quote:
            skipped_empty += 1
            continue

        parts = []
        if conversation_context:
            parts.append(f"[对话上下文] {conversation_context}")
        if category:
            parts.append(f"[分类] {category}")
        parts.append(f"[用户] {user_quote}")
        content = "\n".join(parts)
        metadata = {**metadata_base, "user_quote": user_quote}
        if category:
            metadata["category"] = category
        if conversation_context:
            metadata["conversation_context"] = conversation_context

        try:
            result = _get_mem().add(content, user_id=user_id, metadata=metadata)
            logger.info("[save_memory] mem0.add 原始结果 user=%s result=%s", user_id, result)
            results.append(result)
        except Exception as e:
            logger.error("[save_memory] add 失败 user=%s quote=%r: %s", user_id, user_quote, e)
            failed.append(f"{user_quote[:30]}... ({e})")

    summary = _format_add_results(results) if results else "未保存任何记忆。"
    notes: list[str] = []
    if skipped_empty:
        notes.append(f"跳过 {skipped_empty} 条空 user_quote")
    if failed:
        notes.append(f"失败 {len(failed)} 条：{'; '.join(failed)}")
    if notes:
        summary += "（" + "；".join(notes) + "）"
    return summary


def search_memory(query: str, user_id: str, top_k: int = 5) -> str:
    """
    从用户的长期记忆中检索与查询最相关的内容（格式化输出）。

    Args:
        query: 检索查询，描述你想找的信息。
        user_id: 用户唯一标识。
        top_k: 返回最相关的记忆条数，默认 5。

    Returns:
        编号列表形式的相关记忆，或"未找到"提示。
    """
    memories = search_memories_raw(query, user_id, top_k)

    if not memories:
        return "未找到相关记忆。"

    lines = [
        f"{i + 1}. [id={m.get('id', '—')}] {m['memory']}"
        for i, m in enumerate(memories)
    ]
    return "\n".join(lines)


def search_memories_with_docs(
    query: str,
    user_id: str,
    top_k: int = 5
) -> str:
    """
    检索记忆并附带关联的知识库文档内容。

    实现"记忆先行"检索策略：
    1. 从记忆中检索相关记忆
    2. 提取记忆关联的 doc_id
    3. 用 doc_id 去知识库中检索该文档的相关内容
    4. 返回记忆 + 文档内容

    Args:
        query: 检索查询
        user_id: 用户唯一标识
        top_k: 返回记忆数量

    Returns:
        记忆列表，附带关联文档内容
    """
    memories = search_memories_raw(query, user_id, top_k)

    if not memories:
        return "未找到相关记忆。"

    # 提取有 doc_id 的记忆
    memories_with_doc = []
    doc_ids = set()
    for m in memories:
        doc_id = m.get("metadata", {}).get("doc_id")
        if doc_id:
            memories_with_doc.append(m)
            doc_ids.add(doc_id)

    # 格式化记忆输出
    lines = []
    for i, m in enumerate(memories, 1):
        doc_id = m.get("metadata", {}).get("doc_id")
        source = m.get("metadata", {}).get("source", "")

        if doc_id and source:
            lines.append(
                f"{i}. [id={m.get('id', '—')}] {m['memory']}\n"
                f"   关联文档：{source} (doc_id: {doc_id})"
            )
        else:
            lines.append(f"{i}. [id={m.get('id', '—')}] {m['memory']}")

    # 如果有关联文档，检索文档内容
    if doc_ids:
        try:
            from app.services.rag_service import search_by_doc_ids
            doc_content = search_by_doc_ids(
                query=query,
                user_id=user_id,
                doc_ids=list(doc_ids),
                top_k=3,
            )
            if doc_content and "未找到" not in doc_content:
                lines.append("\n### 关联文档内容")
                lines.append(doc_content)
        except Exception as e:
            logger.error("[search_memories_with_docs] 检索文档内容失败: %s", e)

    return "\n".join(lines)


def delete_memory(memory_id: str, user_id: str) -> str:
    """
    删除指定的一条长期记忆。

    删除前先校验该 memory 是否属于当前用户，防止越权删除。

    Args:
        memory_id: 记忆的唯一 ID，可通过 list_memories 或 search_memory 获取。
        user_id: 用户唯一标识（用于校验归属）。

    Returns:
        删除结果描述。
    """
    try:
        # 直接获取单条记忆校验归属
        memory = _get_mem().get(memory_id)
        if not memory:
            return f"删除失败：记忆 {memory_id} 不存在。"
        if memory.get("user_id") != user_id:
            return f"删除失败：记忆 {memory_id} 不属于用户 {user_id}。"
        _get_mem().delete(memory_id)
        return f"记忆 {memory_id} 已删除。"
    except Exception as e:
        logger.error("[delete_memory] 失败: %s", e)
        return f"删除记忆失败：{e}"


def clear_memories(user_id: str) -> str:
    """
    清空指定用户的全部长期记忆（慎用）。

    Args:
        user_id: 用户唯一标识。

    Returns:
        清空结果描述。
    """
    try:
        _get_mem().delete_all(user_id)
        return f"用户 {user_id} 的全部记忆已清空。"
    except Exception as e:
        logger.error("[clear_memories] 失败: %s", e)
        return f"清空记忆失败：{e}"


def list_memories(user_id: str) -> str:
    """
    列出用户的所有长期记忆（不经过向量检索，直接按 user_id 全量返回）。

    Args:
        user_id: 用户唯一标识。

    Returns:
        带分类标签的编号记忆列表，或"暂无记录"提示。
    """
    try:
        results = _get_mem().get_all(filters={"user_id": user_id})
        memories = results.get("results", [])
        if not memories:
            return "该用户暂无记忆记录。"
        lines = [
            f"{i + 1}. [id={m.get('id', '—')}] [{m.get('metadata', {}).get('category', '—')}] {m['memory']}"
            for i, m in enumerate(memories)
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error("[list_memories] 失败: %s", e)
        return f"获取记忆列表失败：{e}"


def get_memories_by_doc_ids(
    user_id: str,
    doc_ids: List[str]
) -> dict[str, List[dict]]:
    """
    批量获取多个文档的关联记忆。

    使用 metadata filter 在数据库层过滤，避免全量扫描。

    Args:
        user_id: 用户唯一标识
        doc_ids: 文档 ID 列表

    Returns:
        按 doc_id 分组的记忆字典
        {
            "doc_id_1": [memory1, memory2, ...],
            "doc_id_2": [memory3, ...],
        }
    """
    try:
        # 使用 metadata filter 在数据库层过滤
        results = _get_mem().get_all(
            filters={
                "user_id": user_id,
                "metadata.doc_id": {"$in": doc_ids}  # 批量查询
            }
        )

        # 按 doc_id 分组
        memories_by_doc: dict[str, List[dict]] = {}
        for m in results.get("results", []):
            doc_id = m.get("metadata", {}).get("doc_id")
            if doc_id:
                if doc_id not in memories_by_doc:
                    memories_by_doc[doc_id] = []
                memories_by_doc[doc_id].append(m)

        return memories_by_doc

    except Exception as e:
        logger.error("[get_memories_by_doc_ids] 失败: %s", e)
        return {}
