"""
向量数据库抽象基类
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class VectorStore(ABC):
    """向量数据库通用抽象接口"""

    @abstractmethod
    def insert(self, data: list[list[Any]], columns: list[str] | None = None) -> None:
        """批量插入数据，columns 指定字段名（跳过 auto-generated 字段时必传）"""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vectors: list[list[float]],
        top_k: int,
        filters: Optional[str] = None,
        output_fields: Optional[list[str]] = None,
    ) -> list[list[dict[str, Any]]]:
        """向量相似度检索"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, expr: str) -> None:
        """按表达式条件删除数据"""
        raise NotImplementedError

    @abstractmethod
    def query(self, expr: str, output_fields: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """按表达式条件查询数据"""
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> None:
        """刷新数据到持久化存储"""
        raise NotImplementedError
