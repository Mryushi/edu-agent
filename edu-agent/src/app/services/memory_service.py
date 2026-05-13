"""
mem0 + Milvus 长期记忆 Service

封装记忆管理业务逻辑：保存、检索、列出用户的长期记忆。
底层依赖 app.repositories.mem0_store 提供的 MemoryRepository。
"""
import logging
from typing import Any, List, Optional

from app.repositories.mem0_store import get_memory_repository

logger = logging.getLogger(__name__)

_mem = None


def _get_mem():
    """懒加载 MemoryRepository，避免模块导入时初始化外部依赖。"""
    global _mem
    if _mem is None:
        _mem = get_memory_repository()
    return _mem


# ------------------------------------------------------------------ #
# 内部辅助
# ------------------------------------------------------------------ #
def _format_add_result(result: dict) -> str:
    """格式化 mem0 add() 的返回结果为可读字符串。"""
    added = [r.get("memory", "") for r in result.get("results", []) if r.get("event") == "ADD"]
    updated = [r.get("memory", "") for r in result.get("results", []) if r.get("event") == "UPDATE"]
    parts = []
    if added:
        parts.append(f"已保存：{'; '.join(added)}")
    if updated:
        parts.append(f"已更新：{'; '.join(updated)}")
    return "、".join(parts) if parts else "记忆已处理（无新增/更新）"


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


# ------------------------------------------------------------------ #
# 业务接口
# ------------------------------------------------------------------ #
def save_memory(user_id: str, facts: List[Any], conversation_answer_summary: Optional[str] = None) -> str:
    """
    将结构化记忆事实批量保存到用户的长期记忆中。

    Args:
        user_id: 用户唯一标识，用于隔离不同用户的记忆。
        facts: 需要保存的记忆事实列表，每条为 MemoryFact 对象或 dict，包含 user_quote 和可选 category。
        conversation_answer_summary: 本次模型回复的总结，作为记忆上下文存入 metadata。

    Returns:
        描述保存结果的字符串。
    """
    try:
        metadata_base = {}
        if conversation_answer_summary:
            metadata_base["summary"] = conversation_answer_summary

        results = []
        for fact in facts:
            # 兼容 Pydantic model 和 dict
            if isinstance(fact, dict):
                user_quote = fact.get("user_quote", "")
                category = fact.get("category")
            else:
                user_quote = getattr(fact, "user_quote", "")
                category = getattr(fact, "category", None)

            content = f"[用户] {user_quote}"
            metadata = {**metadata_base, "user_quote": user_quote}
            if category:
                metadata["category"] = category

            result = _get_mem().add(content, user_id=user_id, metadata=metadata)
            results.append(result)

        return _format_add_results(results)
    except Exception as e:
        logger.error("[save_memory] 失败: %s", e)
        return f"保存记忆失败：{e}"


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

    Args:
        memory_id: 记忆的唯一 ID，可通过 list_memories 或 search_memory 获取。
        user_id: 用户唯一标识（用于校验和日志）。

    Returns:
        删除结果描述。
    """
    try:
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
