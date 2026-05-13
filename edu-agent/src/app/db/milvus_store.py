"""
Milvus 向量存储通用实现
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from pymilvus import Collection, CollectionSchema

from app.db.connection import MilvusConnectionManager
from app.db.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MilvusVectorStore(VectorStore):
    """
    基于 Milvus 的通用向量存储实现。

    自动管理 collection 的创建、索引建立和数据加载。
    """

    def __init__(
        self,
        collection_name: str,
        fields: list,
        vector_field: str,
        index_params: dict[str, Any],
        metric_type: str = "COSINE",
    ):
        self._conn = MilvusConnectionManager()
        self._collection_name = collection_name
        self._vector_field = vector_field
        self._index_params = index_params
        self._metric_type = metric_type

        self._collection = self._init_collection(fields)

    # ------------------------------------------------------------------ #
    # 内部初始化
    # ------------------------------------------------------------------ #
    def _init_collection(self, fields: list) -> Collection:
        """初始化或获取已有的 collection"""
        self._conn.ensure_connected()

        if not self._conn.has_collection(self._collection_name):
            logger.info("[MilvusStore] 创建 collection: %s", self._collection_name)
            schema = CollectionSchema(fields, description=f"Collection for {self._collection_name}")
            collection = Collection(self._collection_name, schema)
            collection.create_index(self._vector_field, self._index_params)
            logger.info("[MilvusStore] collection 创建完成")
        else:
            collection = Collection(self._collection_name)

        collection.load()
        return collection

    # ------------------------------------------------------------------ #
    # 属性
    # ------------------------------------------------------------------ #
    @property
    def collection(self) -> Collection:
        """底层 Milvus Collection 实例（仅用于需要直接操作的场景）"""
        return self._collection

    # ------------------------------------------------------------------ #
    # VectorStore 接口实现
    # ------------------------------------------------------------------ #
    def insert(self, data: list[list[Any]]) -> None:
        self._collection.insert(data)

    def search(
        self,
        query_vectors: list[list[float]],
        top_k: int,
        filters: Optional[str] = None,
        output_fields: Optional[list[str]] = None,
    ) -> list[list[dict[str, Any]]]:
        search_params = {
            "metric_type": self._metric_type,
            "params": {"ef": 64},
        }
        results = self._collection.search(
            data=query_vectors,
            anns_field=self._vector_field,
            param=search_params,
            limit=top_k,
            expr=filters,
            output_fields=output_fields or [],
        )

        # 将 pymilvus 的 Hit 对象转换为统一 dict 格式
        formatted: list[list[dict[str, Any]]] = []
        for result in results:
            hits: list[dict[str, Any]] = []
            for hit in result:
                hit_dict: dict[str, Any] = {
                    "id": hit.id,
                    "distance": hit.distance,
                }
                for field in (output_fields or []):
                    hit_dict[field] = hit.entity.get(field)
                hits.append(hit_dict)
            formatted.append(hits)
        return formatted

    def delete(self, expr: str) -> None:
        self._collection.delete(expr)

    def query(self, expr: str, output_fields: Optional[list[str]] = None) -> list[dict[str, Any]]:
        return self._collection.query(expr=expr, output_fields=output_fields or [])

    def flush(self) -> None:
        self._collection.flush()
