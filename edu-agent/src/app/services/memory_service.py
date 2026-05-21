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
    memories_added = []
    memories_updated = []
    for result in results:
        for r in result.get("results", []):
            if r.get("event") == "ADD":
                total_added += 1
                memories_added.append(r.get("memory", ""))
            elif r.get("event") == "UPDATE":
                total_updated += 1
                memories_updated.append(r.get("memory", ""))
    parts = []
    if total_added:
        parts.append(f"已保存 {total_added} 条：{'; '.join(memories_added)}")
    if total_updated:
        parts.append(f"已更新 {total_updated} 条：{'; '.join(memories_updated)}")
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
# 业务接口
# ------------------------------------------------------------------ #
def save_memory(
    user_id: str,
    facts: List[Any],
    conversation_answer_summary: Optional[str] = None,
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
    if conversation_answer_summary:
        metadata_base["summary"] = conversation_answer_summary
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

        content = f"[用户] {user_quote}"
        metadata = {**metadata_base, "user_quote": user_quote}
        if category:
            metadata["category"] = category

        try:
            result = _get_mem().add(content, user_id=user_id, metadata=metadata)
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
    从用户的长期记忆中检索与查询最相关的内容。

    Args:
        query: 检索查询，描述你想找的信息。
        user_id: 用户唯一标识。
        top_k: 返回最相关的记忆条数，默认 5。

    Returns:
        编号列表形式的相关记忆，或"未找到"提示。
    """
    try:
        results = _get_mem().search(query=query, filters={"user_id": user_id}, top_k=top_k)
        memories = results.get("results", [])
        if not memories:
            return "未找到相关记忆。"
        lines = [f"{i + 1}. [id={m.get('id', '—')}] {m['memory']}" for i, m in enumerate(memories)]
        return "\n".join(lines)
    except Exception as e:
        logger.error("[search_memory] 失败: %s", e)
        return f"检索记忆失败：{e}"


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
        # 先查出该用户的全部记忆，校验 memory_id 归属
        all_results = _get_mem().get_all(filters={"user_id": user_id})
        user_memory_ids = {m.get("id") for m in all_results.get("results", [])}
        if memory_id not in user_memory_ids:
            return f"删除失败：记忆 {memory_id} 不属于用户 {user_id}，或该记忆不存在。"
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


def list_memories_by_doc(user_id: str, doc_id: str) -> str:
    """
    列出与指定 RAG 文档关联的所有长期记忆（反向查询）。

    Args:
        user_id: 用户唯一标识。
        doc_id: RAG 文档的唯一 ID（通过 list_knowledge_documents 获取）。

    Returns:
        带分类标签的编号记忆列表，或"暂无关联记忆"提示。
    """
    try:
        results = _get_mem().get_all(filters={"user_id": user_id})
        memories = [
            m for m in results.get("results", [])
            if m.get("metadata", {}).get("doc_id") == doc_id
        ]
        if not memories:
            return "该文档暂无关联记忆。"
        lines = [
            f"{i + 1}. [id={m.get('id', '—')}] [{m.get('metadata', {}).get('category', '—')}] {m['memory']}"
            for i, m in enumerate(memories)
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error("[list_memories_by_doc] 失败: %s", e)
        return f"获取文档关联记忆失败：{e}"
