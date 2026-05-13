"""
RAG 知识库 Repository

基于 app.db.milvus_store.MilvusVectorStore 实现的数据访问层。
职责：纯粹的向量数据 CRUD，不处理向量化、文件解析等业务逻辑。

Schema:
    id          VARCHAR  主键，格式: {doc_id}_{chunk_index:04d}
    vector      FLOAT_VECTOR
    text        VARCHAR  chunk 原文
    user_id     VARCHAR  用于过滤隔离
    doc_id      VARCHAR  同一文档的 chunks 共享
    source      VARCHAR  原始文件名
    chunk_index INT64
    created_at  INT64    Unix timestamp（秒）
"""
from __future__ import annotations

import logging
import time
from typing import Any

from pymilvus import DataType, FieldSchema

from app.core.config import settings
from app.db.milvus_store import MilvusVectorStore

logger = logging.getLogger(__name__)

_MAX_TEXT_LEN = 4096
_MAX_ID_LEN = 64
_MAX_STR_LEN = 256


class KnowledgeRepository:
    """
    RAG 知识库 Repository。

    接收已向量化的数据执行 Milvus CRUD，不负责 embedding。
    """

    def __init__(self, store: MilvusVectorStore):
        self._store = store

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #
    def insert(self, chunks: list, vectors: list[list[float]]) -> int:
        """
        批量插入已向量化的 Chunk 列表。

        Args:
            chunks: Chunk 对象列表，需包含 chunk_id / text / user_id / doc_id / source / chunk_index 属性。
            vectors: 与 chunks 一一对应的向量列表。

        Returns:
            实际插入的条数。
        """
        if not chunks or not vectors:
            return 0
        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks 数量 ({len(chunks)}) 与 vectors 数量 ({len(vectors)}) 不一致"
            )

        now = int(time.time())
        data = [
            [c.chunk_id for c in chunks],
            vectors,
            [c.text[:_MAX_TEXT_LEN] for c in chunks],
            [c.user_id for c in chunks],
            [c.doc_id for c in chunks],
            [c.source for c in chunks],
            [c.chunk_index for c in chunks],
            [now] * len(chunks),
        ]
        self._store.insert(data)
        self._store.flush()
        logger.info(
            "[KnowledgeRepository] 插入 %d 个 chunks，doc_id=%s",
            len(chunks), chunks[0].doc_id,
        )
        return len(chunks)

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    def search(
        self, query_vec: list[float], user_id: str, top_k: int
    ) -> list[dict]:
        """
        语义检索：使用已向量化的 query 向量做 ANN 检索。

        Args:
            query_vec: query 的向量表示。
            user_id: 用户隔离标识。
            top_k: 返回最相关的条数。

        Returns:
            命中列表，每条包含 text / source / doc_id / chunk_index / score。
        """
        results = self._store.search(
            query_vectors=[query_vec],
            top_k=top_k,
            filters=f'user_id == "{user_id}"',
            output_fields=["text", "source", "doc_id", "chunk_index"],
        )
        return [
            {
                "text": hit["text"],
                "source": hit["source"],
                "doc_id": hit["doc_id"],
                "chunk_index": hit["chunk_index"],
                "score": hit["distance"],
            }
            for hit in results[0]
        ]

    # ------------------------------------------------------------------ #
    # 删除
    # ------------------------------------------------------------------ #
    def delete_by_doc_id(self, doc_id: str, user_id: str) -> int:
        """
        删除指定文档的所有 chunks（按 doc_id + user_id 过滤）。

        Returns:
            实际删除的条数。
        """
        expr = f'doc_id == "{doc_id}" && user_id == "{user_id}"'
        res = self._store.query(expr=expr, output_fields=["id"])
        ids = [r["id"] for r in res]
        if ids:
            id_list = ", ".join(f'"{i}"' for i in ids)
            self._store.delete(f"id in [{id_list}]")
            self._store.flush()
            logger.info(
                "[KnowledgeRepository] 删除 doc_id=%s，共 %d 个 chunks",
                doc_id, len(ids),
            )
        return len(ids)

    # ------------------------------------------------------------------ #
    # 列表
    # ------------------------------------------------------------------ #
    def list_by_user_id(self, user_id: str) -> list[dict]:
        """
        列出指定用户已入库的所有文档（按 doc_id 聚合）。

        Returns:
            文档元信息列表，包含 doc_id / source / chunk_count / created_at。
        """
        res = self._store.query(
            expr=f'user_id == "{user_id}"',
            output_fields=["doc_id", "source", "chunk_index", "created_at"],
        )
        docs: dict[str, dict] = {}
        for r in res:
            did = r["doc_id"]
            if did not in docs:
                docs[did] = {
                    "doc_id": did,
                    "source": r["source"],
                    "chunk_count": 0,
                    "created_at": r["created_at"],
                }
            docs[did]["chunk_count"] += 1
            if r["created_at"] < docs[did]["created_at"]:
                docs[did]["created_at"] = r["created_at"]
        return sorted(docs.values(), key=lambda x: x["created_at"], reverse=True)


# ------------------------------------------------------------------ #
# 默认实例工厂
# ------------------------------------------------------------------ #
def _create_default_store() -> MilvusVectorStore:
    """创建默认的 RAG MilvusVectorStore（懒加载）。"""
    dim = settings.MEMORY_EMBEDDING_DIMS
    fields = [
        FieldSchema("id", DataType.VARCHAR, max_length=_MAX_ID_LEN, is_primary=True),
        FieldSchema("vector", DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema("text", DataType.VARCHAR, max_length=_MAX_TEXT_LEN),
        FieldSchema("user_id", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("doc_id", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("source", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("chunk_index", DataType.INT64),
        FieldSchema("created_at", DataType.INT64),
    ]
    index_params = {
        "index_type": "HNSW",
        "metric_type": settings.MILVUS_METRIC_TYPE,
        "params": {"M": 16, "efConstruction": 200},
    }
    return MilvusVectorStore(
        collection_name=settings.MILVUS_RAG_COLLECTION,
        fields=fields,
        vector_field="vector",
        index_params=index_params,
        metric_type=settings.MILVUS_METRIC_TYPE,
    )


_repo_instance: KnowledgeRepository | None = None


def get_knowledge_repository() -> KnowledgeRepository:
    """获取 KnowledgeRepository 全局单例。"""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = KnowledgeRepository(_create_default_store())
    return _repo_instance
