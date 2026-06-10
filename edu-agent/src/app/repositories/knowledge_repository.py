"""
RAG 知识库 Repository

基于 app.db.milvus_store.MilvusVectorStore 实现的 RAG 数据访问层。
职责仅限于 Chunk → Milvus 字段映射和明确的 CRUD 操作；增量判断、embedding、
文件解析、检索流水线组合等业务编排都放在 services/rag_service.py。

Schema:
    id              VARCHAR  主键，格式: {doc_id}_{chunk_index:04d}
    text            VARCHAR  chunk 原文 (enable_analyzer=True, chinese analyzer)
    dense_vector    FLOAT_VECTOR  1024-dim qwen3 dense embedding
    sparse_vector   SPARSE_FLOAT_VECTOR  BM25 Function 自动生成
    user_id         VARCHAR  用于过滤隔离
    doc_id          VARCHAR  同一文档的 chunks 共享
    source          VARCHAR  原始文件名
    chunk_index     INT64
    created_at      INT64    Unix timestamp（秒）
    content_hash    VARCHAR  内容 SHA-256 前 16 位
    section_path    VARCHAR  标题层级面包屑（如 "第一章 > 1.1 引言"）
    heading_level   INT64    标题深度（0 表示无标题）
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from pymilvus import DataType, FieldSchema, Function, FunctionType

from app.core.config import settings
from app.db.milvus_store import MilvusVectorStore

logger = logging.getLogger(__name__)

_MAX_TEXT_LEN = 65535
_MAX_ID_LEN = 64
_MAX_STR_LEN = 256
_MAX_SECTION_PATH_LEN = 512

_INSERT_COLUMNS = [
    "id", "text", "dense_vector", "user_id", "doc_id",
    "source", "chunk_index", "created_at", "content_hash",
    "section_path", "heading_level",
]

# Milvus BM25 内置中文分词配置（使用 Jieba）。
# 旧 collection 未启用该 analyzer 时，校验逻辑会要求重建 collection。
_CHINESE_ANALYZER_PARAMS = {
    "tokenizer": "jieba",
    "filter": ["lowercase"],
}


class KnowledgeRepository:
    """RAG 知识库 Repository。

    仅执行 service 发出的明确 CRUD 命令：不做增量判断、不做 embedding、
    不重新过滤 content_hash。
    """

    def __init__(self, store: MilvusVectorStore):
        self._store = store

    # ------------------------------------------------------------------ #
    # 写入
    # ------------------------------------------------------------------ #
    def insert_chunks(self, chunks: list, dense_vectors: list[list[float]]) -> int:
        """批量插入已向量化的 Chunk 列表。

        Repository 不做增量判断；调用方需自行保证 chunk_id 与已有数据不冲突
        （新增 chunk 或在调用前 `delete_chunks_by_ids` 删除旧版本）。

        Args:
            chunks: Chunk 对象列表，每条需提供 chunk_id / text / user_id /
                doc_id / source / chunk_index / content_hash，以及可选的
                metadata.section_path / metadata.heading_level。
            dense_vectors: 与 chunks 一一对应的稠密向量。

        Returns:
            实际插入的条数。
        """
        if not chunks:
            return 0
        if len(chunks) != len(dense_vectors):
            raise ValueError(
                f"chunks 数量 ({len(chunks)}) 与 dense_vectors 数量 ({len(dense_vectors)}) 不一致"
            )

        for c in chunks:
            if len(c.text) > _MAX_TEXT_LEN:
                raise ValueError(
                    f"chunk_id={c.chunk_id} 文本长度 {len(c.text)} 超过 Milvus VARCHAR 上限 {_MAX_TEXT_LEN}，"
                    f"请在 service/chunking 层完成安全切分"
                )

        now = int(time.time())
        data = [
            [c.chunk_id for c in chunks],
            [c.text for c in chunks],
            dense_vectors,
            [c.user_id for c in chunks],
            [c.doc_id for c in chunks],
            [c.source for c in chunks],
            [c.chunk_index for c in chunks],
            [now] * len(chunks),
            [c.content_hash for c in chunks],
            [self._truncate(c.metadata.get("section_path", ""), _MAX_SECTION_PATH_LEN) for c in chunks],
            [int(c.metadata.get("heading_level", 0)) for c in chunks],
        ]
        self._store.insert(data, columns=_INSERT_COLUMNS)
        self._store.flush()
        logger.info(
            "[KnowledgeRepository] insert_chunks: %d 条，doc_id=%s",
            len(chunks), chunks[0].doc_id,
        )
        return len(chunks)

    @staticmethod
    def _truncate(value: str, max_len: int) -> str:
        return value if len(value) <= max_len else value[: max_len - 1] + "…"

    # ------------------------------------------------------------------ #
    # Hash 查询（供 service 层做增量决策）
    # ------------------------------------------------------------------ #
    def get_hashes_by_doc_id(self, doc_id: str, user_id: str) -> dict[str, str]:
        """返回指定文档（按 user_id 隔离）的 {chunk_id: content_hash} 映射。

        异常直接向上传播，由调用方决定重试或降级策略；
        不返回空字典，避免调用方误判为"无已有记录"导致重复插入。
        """
        res = self._store.query(
            expr=f'doc_id == "{doc_id}" && user_id == "{user_id}"',
            output_fields=["id", "content_hash"],
        )
        return {r["id"]: r.get("content_hash", "") for r in res}

    # ------------------------------------------------------------------ #
    # 删除
    # ------------------------------------------------------------------ #
    def delete_chunks_by_ids(self, chunk_ids: Iterable[str], user_id: str) -> int:
        """按 chunk_id 列表删除 chunks，强制带上 user_id 防越权。"""
        ids = list(chunk_ids)
        if not ids:
            return 0
        id_list = ", ".join(f'"{i}"' for i in ids)
        expr = f'id in [{id_list}] && user_id == "{user_id}"'
        res = self._store.query(expr=expr, output_fields=["id"])
        matched = [r["id"] for r in res]
        if matched:
            self._store.delete(expr)
            self._store.flush()
            logger.info(
                "[KnowledgeRepository] delete_chunks_by_ids: %d 条 user_id=%s",
                len(matched), user_id,
            )
        return len(matched)

    def delete_document(self, doc_id: str, user_id: str) -> int:
        """按 doc_id + user_id 删除整份文档的所有 chunks。"""
        expr = f'doc_id == "{doc_id}" && user_id == "{user_id}"'
        res = self._store.query(expr=expr, output_fields=["id"])
        ids = [r["id"] for r in res]
        if ids:
            self._store.delete(expr)
            self._store.flush()
            logger.info(
                "[KnowledgeRepository] delete_document: doc_id=%s user_id=%s 共 %d chunks",
                doc_id, user_id, len(ids),
            )
        return len(ids)

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    def hybrid_search(
        self,
        dense_vector: list[float],
        query_text: str,
        user_id: str,
        top_k: int,
        fetch_k: int,
        doc_ids: list[str] | None = None,
    ) -> tuple[list[dict], bool]:
        """混合检索：dense ANN + sparse BM25，RRF 融合。

        Args:
            doc_ids: 可选，限制在指定文档中检索

        Returns:
            (命中列表, hybrid_success)。hybrid_success=False 表示底层已降级为 dense-only。
        """
        # 构建过滤条件
        filters = f'user_id == "{user_id}"'
        if doc_ids:
            doc_id_filter = ", ".join([f'"{did}"' for did in doc_ids])
            filters += f' && doc_id in [{doc_id_filter}]'

        hits, hybrid_success = self._store.hybrid_search(
            dense_vector=dense_vector,
            query_text=query_text,
            dense_field="dense_vector",
            sparse_field="sparse_vector",
            top_k=top_k,
            fetch_k=fetch_k,
            filters=filters,
            output_fields=["text", "source", "doc_id", "chunk_index", "section_path"],
            dense_metric=settings.MILVUS_METRIC_TYPE,
        )
        formatted = [
            {
                "text": h["text"],
                "source": h["source"],
                "doc_id": h["doc_id"],
                "chunk_index": h["chunk_index"],
                "section_path": h.get("section_path", "") or "",
                "score": h["distance"],
            }
            for h in hits
        ]
        return formatted, hybrid_success

    # ------------------------------------------------------------------ #
    # 列表
    # ------------------------------------------------------------------ #
    def list_by_user_id(self, user_id: str) -> list[dict]:
        """列出指定用户已入库的所有文档（按 doc_id 聚合）。"""
        res = self._store.query(
            expr=f'user_id == "{user_id}"',
            output_fields=["doc_id", "source", "chunk_index", "created_at"],
        )
        # Python 端按 doc_id 聚合
        grouped: dict[str, dict] = {}
        for r in res:
            did = r["doc_id"]
            if did not in grouped:
                grouped[did] = {
                    "doc_id": did,
                    "source": r["source"],
                    "chunk_count": 0,
                    "created_at": r["created_at"],
                }
            grouped[did]["chunk_count"] += 1
        return sorted(grouped.values(), key=lambda x: x["created_at"], reverse=True)


# ------------------------------------------------------------------ #
# 默认实例工厂
# ------------------------------------------------------------------ #
def _create_default_store() -> MilvusVectorStore:
    """创建默认的 RAG MilvusVectorStore（懒加载）。"""
    dim = settings.embedding_dimensions
    fields = [
        FieldSchema("id", DataType.VARCHAR, max_length=_MAX_ID_LEN, is_primary=True),
        FieldSchema(
            "text",
            DataType.VARCHAR,
            max_length=_MAX_TEXT_LEN,
            enable_analyzer=True,
            analyzer_params=_CHINESE_ANALYZER_PARAMS,
        ),
        FieldSchema("dense_vector", DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema("sparse_vector", DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema("user_id", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("doc_id", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("source", DataType.VARCHAR, max_length=_MAX_STR_LEN),
        FieldSchema("chunk_index", DataType.INT64),
        FieldSchema("created_at", DataType.INT64),
        FieldSchema("content_hash", DataType.VARCHAR, max_length=32),
        FieldSchema("section_path", DataType.VARCHAR, max_length=_MAX_SECTION_PATH_LEN),
        FieldSchema("heading_level", DataType.INT64),
    ]
    bm25_fn = Function(
        name="text_bm25_emb",
        input_field_names=["text"],
        output_field_names=["sparse_vector"],
        function_type=FunctionType.BM25,
    )
    return MilvusVectorStore(
        collection_name=settings.MILVUS_RAG_COLLECTION,
        fields=fields,
        vector_field="dense_vector",
        index_params={
            "index_type": "HNSW",
            "metric_type": settings.MILVUS_METRIC_TYPE,
            "params": {"M": 16, "efConstruction": 200},
        },
        metric_type=settings.MILVUS_METRIC_TYPE,
        functions=[bm25_fn],
        extra_indexes=[
            {
                "field_name": "sparse_vector",
                "index_name": "sparse_idx",
                "index_params": {
                    "index_type": "SPARSE_INVERTED_INDEX",
                    "metric_type": "BM25",
                },
            },
        ],
    )


_repo_instance: KnowledgeRepository | None = None


def get_knowledge_repository() -> KnowledgeRepository:
    """获取 KnowledgeRepository 全局单例。"""
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = KnowledgeRepository(_create_default_store())
    return _repo_instance
