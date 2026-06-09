"""
Milvus 向量存储通用实现

通用 Milvus 适配层。只处理 collection 初始化、schema/index/function 校验和原始
PyMilvus API 调用，不包含 RAG 业务概念（doc_id / user_id / chunk_id 等）。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from pymilvus import AnnSearchRequest, Collection, CollectionSchema, RRFRanker

from app.db.connection import MilvusConnectionManager
from app.db.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MilvusVectorStore(VectorStore):
    """
    基于 Milvus 的通用向量存储实现。

    自动管理 collection 的创建、索引建立和数据加载。
    支持 BM25 Function（sparse vector）和 hybrid search。
    """

    def __init__(
        self,
        collection_name: str,
        fields: list,
        vector_field: str,
        index_params: dict[str, Any],
        metric_type: str = "COSINE",
        functions: list | None = None,
        extra_indexes: list[dict[str, Any]] | None = None,
    ):
        self._conn = MilvusConnectionManager()
        self._collection_name = collection_name
        self._vector_field = vector_field
        self._index_params = index_params
        self._metric_type = metric_type
        self._functions = functions
        self._extra_indexes = extra_indexes or []

        self._collection = self._init_collection(fields)

    # ------------------------------------------------------------------ #
    # 内部初始化
    # ------------------------------------------------------------------ #
    def _init_collection(self, fields: list) -> Collection:
        """初始化或获取已有的 collection，并校验 schema / index / function 一致性。"""
        self._conn.ensure_connected()

        if not self._conn.has_collection(self._collection_name):
            logger.info("[MilvusStore] 创建 collection: %s", self._collection_name)
            schema_kwargs = {"description": f"Collection for {self._collection_name}"}
            if self._functions:
                schema_kwargs["functions"] = self._functions
            schema = CollectionSchema(fields, **schema_kwargs)
            collection = Collection(self._collection_name, schema)
            collection.create_index(self._vector_field, self._index_params)
            for idx_cfg in self._extra_indexes:
                collection.create_index(**idx_cfg)
            logger.info(
                "[MilvusStore] collection 创建完成: %s（fields=%d, functions=%d, extra_indexes=%d）",
                self._collection_name, len(fields),
                len(self._functions or []), len(self._extra_indexes),
            )
        else:
            collection = Collection(self._collection_name)
            self._validate_schema(collection, fields)

        collection.load()
        return collection

    def _validate_schema(self, collection: Collection, expected_fields: list) -> None:
        """校验已有 collection 的 fields / functions / extra indexes 是否与预期一致。"""
        existing = collection.schema
        existing_fields = {f.name: f.dtype for f in existing.fields}
        expected = {f.name: f.dtype for f in expected_fields}

        issues: list[str] = []

        missing = [name for name in expected if name not in existing_fields]
        if missing:
            issues.append(f"  缺失字段: {missing}")

        type_mismatch = [
            f"{name} (expected {expected[name]}, got {existing_fields[name]})"
            for name in expected
            if name in existing_fields and existing_fields[name] != expected[name]
        ]
        if type_mismatch:
            issues.append(f"  类型不匹配: {type_mismatch}")

        extra = [name for name in existing_fields if name not in expected]
        if extra:
            issues.append(f"  多余字段: {extra}")

        # 校验 BM25 等 Function 配置
        if self._functions:
            existing_fn_names = {fn.name for fn in self._collection_functions(existing)}
            for fn in self._functions:
                if fn.name not in existing_fn_names:
                    issues.append(f"  缺失 Function: {fn.name}")

        # 校验 extra index（如 sparse_vector 的 inverted index）
        if self._extra_indexes:
            try:
                existing_index_names = {idx.index_name for idx in collection.indexes}
            except Exception:
                existing_index_names = set()
            for idx_cfg in self._extra_indexes:
                idx_name = idx_cfg.get("index_name")
                if idx_name and idx_name not in existing_index_names:
                    issues.append(
                        f"  缺失 Index: {idx_name} (field={idx_cfg.get('field_name')})"
                    )

        if not issues:
            return

        lines = [
            f"Milvus collection '{self._collection_name}' 配置不一致，无法继续运行：",
            *issues,
            "",
            "已有 collection 与新 schema / index / function 配置不兼容。",
            f"修复办法：在 Milvus 中删除旧 collection（drop_collection('{self._collection_name}')），重启服务后将按新配置自动重建。",
        ]
        msg = "\n".join(lines)
        logger.error("[MilvusStore] %s", msg)
        raise RuntimeError(msg)

    @staticmethod
    def _collection_functions(schema: CollectionSchema) -> list:
        """读取 schema.functions（兼容旧版 pymilvus）。"""
        return list(getattr(schema, "functions", None) or [])

    # ------------------------------------------------------------------ #
    # 属性
    # ------------------------------------------------------------------ #
    @property
    def collection(self) -> Collection:
        """底层 Milvus Collection 实例（仅用于需要直接操作的场景）"""
        return self._collection

    @property
    def collection_name(self) -> str:
        return self._collection_name

    # ------------------------------------------------------------------ #
    # VectorStore 接口实现
    # ------------------------------------------------------------------ #
    def insert(self, data: list[list[Any]], columns: list[str] | None = None) -> None:
        if columns:
            self._collection.insert(data, columns=columns)
        else:
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

        formatted: list[list[dict[str, Any]]] = []
        for result in results:
            hits: list[dict[str, Any]] = []
            for hit in result:
                hit_dict: dict[str, Any] = {"id": hit.id, "distance": hit.distance}
                for field_name in (output_fields or []):
                    hit_dict[field_name] = hit.entity.get(field_name)
                hits.append(hit_dict)
            formatted.append(hits)
        return formatted

    def hybrid_search(
        self,
        dense_vector: list[float],
        query_text: str,
        dense_field: str,
        sparse_field: str,
        top_k: int,
        fetch_k: int,
        filters: str,
        output_fields: list[str],
        dense_metric: str = "COSINE",
        sparse_metric: str = "BM25",
    ) -> tuple[list[dict[str, Any]], bool]:
        """Milvus 原生混合检索：dense ANN + sparse BM25，RRF 融合。

        Args:
            dense_vector: qwen3 稠密向量。
            query_text: 原始查询文本，用于 BM25 sparse search。
            dense_field: 稠密向量字段名。
            sparse_field: 稀疏向量字段名（BM25 Function 输出）。
            top_k: 最终返回条数。
            fetch_k: 每路检索的候选数。
            filters: Milvus 过滤表达式。
            output_fields: 返回字段列表。
            dense_metric: dense 向量度量类型。
            sparse_metric: sparse 度量类型，BM25 Function 应使用 "BM25"。

        Returns:
            (命中列表, hybrid_success)。hybrid_success=False 表示已降级为 dense-only。
        """
        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field=dense_field,
            param={"metric_type": dense_metric, "params": {"ef": 64}},
            limit=fetch_k,
            expr=filters,
        )
        sparse_req = AnnSearchRequest(
            data=[query_text],
            anns_field=sparse_field,
            param={"metric_type": sparse_metric},
            limit=fetch_k,
            expr=filters,
        )
        try:
            results = self._collection.hybrid_search(
                reqs=[dense_req, sparse_req],
                rerank=RRFRanker(),
                limit=top_k,
                output_fields=output_fields,
            )
            formatted = self._format_hybrid_hits(results[0], output_fields)
            logger.info(
                "[MilvusStore] hybrid_search ok: collection=%s top_k=%d fetch_k=%d hits=%d dense_field=%s sparse_field=%s",
                self._collection_name, top_k, fetch_k, len(formatted),
                dense_field, sparse_field,
            )
            return formatted, True
        except Exception as e:
            logger.error(
                "[MilvusStore] hybrid_search 失败，降级为 dense-only: "
                "collection=%s dense_field=%s sparse_field=%s filters=%s "
                "query=%r dense_metric=%s sparse_metric=%s err=%r",
                self._collection_name, dense_field, sparse_field, filters,
                query_text, dense_metric, sparse_metric, e,
            )
            fallback = self.search(
                query_vectors=[dense_vector],
                top_k=top_k,
                filters=filters,
                output_fields=output_fields,
            )[0]
            return fallback, False

    @staticmethod
    def _format_hybrid_hits(hits, output_fields: list[str]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for hit in hits:
            hit_dict: dict[str, Any] = {"id": hit.id, "distance": hit.distance}
            for field_name in output_fields:
                hit_dict[field_name] = hit.entity.get(field_name)
            formatted.append(hit_dict)
        return formatted

    def delete(self, expr: str) -> None:
        self._collection.delete(expr)

    def query(
        self,
        expr: str,
        output_fields: Optional[list[str]] = None,
        group_by_field: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """查询数据。

        Args:
            expr: 过滤表达式
            output_fields: 返回字段列表
            group_by_field: 分组字段（Milvus 2.3+ 支持）
        """
        kwargs = {"expr": expr, "output_fields": output_fields or []}
        if group_by_field:
            kwargs["group_by_field"] = group_by_field
        return self._collection.query(**kwargs)

    def flush(self) -> None:
        self._collection.flush()
