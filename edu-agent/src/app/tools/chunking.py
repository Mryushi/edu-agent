"""
文本分块引擎

使用 RecursiveCharacterTextSplitter 对解析后的文本进行分块。
分隔符优先级：段落 → 换行 → 句号 → 空格 → 字符级，自然尊重文档结构。
每个 Chunk 携带完整 metadata，便于后续存储和溯源。
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# 中英文混合场景的分隔符优先级
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]


@dataclass
class Chunk:
    """单个文本块"""
    text: str                    # 块文本内容
    chunk_index: int             # 在文档中的序号（0-based）
    doc_id: str                  # 所属文档 ID（由调用方传入）
    source: str                  # 原始文件名
    user_id: str                 # 所属用户
    metadata: dict[str, Any] = field(default_factory=dict)  # 扩展元数据

    @property
    def chunk_id(self) -> str:
        """唯一 ID：doc_id + chunk_index"""
        return f"{self.doc_id}_{self.chunk_index:04d}"


def _make_doc_id(filename: str, user_id: str) -> str:
    """
    根据文件名 + user_id 生成稳定的 doc_id（MD5 前 16 位）。
    同一用户上传同名文件会得到相同 doc_id，便于幂等覆盖。
    """
    raw = f"{user_id}::{filename}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def split_text(
    text: str,
    filename: str,
    user_id: str,
    doc_id: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    """
    将文本切分为带 metadata 的 Chunk 列表。

    Args:
        text: 待分块的原始文本。
        filename: 原始文件名，用于 metadata 溯源。
        user_id: 所属用户 ID。
        doc_id: 文档 ID，不传则自动生成。
        chunk_size: 块大小（字符数），默认读取 settings.RAG_CHUNK_SIZE。
        chunk_overlap: 块重叠（字符数），默认读取 settings.RAG_CHUNK_OVERLAP。
        extra_metadata: 附加到每个 Chunk 的额外元数据。

    Returns:
        Chunk 列表，空文本返回空列表。
    """
    if not text or not text.strip():
        logger.warning("[Chunking] 文本为空，跳过分块: %s", filename)
        return []

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        # 兼容旧版 langchain
        from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

    _chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
    _chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
    _doc_id = doc_id or _make_doc_id(filename, user_id)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_chunk_size,
        chunk_overlap=_chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )

    raw_chunks = splitter.split_text(text)
    logger.info("[Chunking] %s → %d 个块 (size=%d, overlap=%d)",
                filename, len(raw_chunks), _chunk_size, _chunk_overlap)

    base_meta = extra_metadata or {}
    chunks = [
        Chunk(
            text=chunk_text,
            chunk_index=i,
            doc_id=_doc_id,
            source=filename,
            user_id=user_id,
            metadata={**base_meta},
        )
        for i, chunk_text in enumerate(raw_chunks)
    ]
    return chunks


def make_doc_id(filename: str, user_id: str) -> str:
    """公开的 doc_id 生成函数，供外部模块复用。"""
    return _make_doc_id(filename, user_id)
