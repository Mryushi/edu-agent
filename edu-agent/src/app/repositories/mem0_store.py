"""
mem0 长期记忆 Repository

基于 mem0.Memory 的数据访问层封装，统一提供 add / search / get_all 接口。
配置统一由 app.core.config.Settings.get_mem0_config() 提供。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from mem0 import Memory

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryRepository:
    """mem0 Memory 客户端的 Repository 封装。"""

    def __init__(self, mem: Memory):
        self._mem = mem

    def add(self, content: str, user_id: str, metadata: Optional[dict[str, Any]] = None) -> dict:
        """保存记忆到长期存储。"""
        return self._mem.add(content, user_id=user_id, metadata=metadata or {})

    def search(self, query: str, filters: dict[str, Any], top_k: int = 5) -> dict:
        """语义检索记忆。"""
        return self._mem.search(query=query, filters=filters, top_k=top_k)

    def get_all(self, filters: dict[str, Any]) -> dict:
        """全量列出符合条件的记忆。"""
        return self._mem.get_all(filters=filters)

    def get(self, memory_id: str) -> dict:
        """根据 memory_id 获取单条记忆。"""
        return self._mem.get(memory_id)

    def delete(self, memory_id: str) -> dict:
        """根据 memory_id 删除单条记忆。"""
        return self._mem.delete(memory_id)

    def delete_all(self, user_id: str) -> dict:
        """删除指定用户的全部记忆。"""
        return self._mem.delete_all(user_id=user_id)


# ------------------------------------------------------------------ #
# 默认实例工厂
# ------------------------------------------------------------------ #
_repo_instance: Optional[MemoryRepository] = None


def get_memory_repository() -> MemoryRepository:
    """获取 MemoryRepository 全局单例（懒加载）。"""
    global _repo_instance
    if _repo_instance is None:
        config = settings.get_mem0_config()
        logger.info("[mem0] 初始化 Memory，Milvus: %s，collection: %s",
                    settings.MILVUS_URL, settings.MEM0_COLLECTION)
        mem = Memory.from_config(config)
        _repo_instance = MemoryRepository(mem)
    return _repo_instance
