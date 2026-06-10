"""
文本分块引擎 — Markdown 感知版

- 保护代码块（```）和表格不被截断
- 按 #/##/### 标题拆分 section，并维护标题层级栈（breadcrumb）
- 段落级合并，超长按句子切分（。！？）
- 短尾合并（< RAG_CHUNK_MIN 的片段合并到前一个 chunk）
- 安全长度上限（_MAX_SAFE_TEXT_LEN）防止 Milvus VARCHAR 静默截断
- 每个 Chunk 带 content_hash 用于增量 embedding，并在 metadata 中保存
  section_path / heading_level 等结构化信息
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)


# 单个 chunk 文本最大长度（必须严格小于 Milvus VARCHAR max_length=4096）。
# 任何超过该值的 chunk 会按安全边界进一步拆分，避免 Repository 静默截断。
# 可通过环境变量 RAG_CHUNK_MAX_LEN 覆盖，默认 4000。
_MAX_SAFE_TEXT_LEN = settings.RAG_CHUNK_MAX_LEN

# Milvus VARCHAR 硬上限，不可配置，作为最终兜底。
_MILVUS_VARCHAR_MAX = 4096


@dataclass
class Chunk:
    """单个文本块"""
    text: str
    chunk_index: int
    doc_id: str
    source: str
    user_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}_{self.chunk_index:04d}"

    @property
    def section_path(self) -> str:
        return self.metadata.get("section_path", "")

    @property
    def heading_level(self) -> int:
        return int(self.metadata.get("heading_level", 0))

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.text.encode("utf-8")
            ).hexdigest()[:16]


@dataclass
class _Piece:
    """分块中间态：携带 section 上下文，便于最终构建 Chunk。"""
    text: str
    section_path: str
    heading_level: int


def _make_doc_id(filename: str, user_id: str) -> str:
    raw = f"{user_id}::{filename}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def make_doc_id(filename: str, user_id: str) -> str:
    return _make_doc_id(filename, user_id)


# ------------------------------------------------------------------ #
# 受保护区间（代码块、表格）
# ------------------------------------------------------------------ #
def _find_protected_ranges(text: str) -> list[tuple[int, int]]:
    """找出不可分割的区间：围栏代码块和表格行。"""
    ranges: list[tuple[int, int]] = []
    for m in re.finditer(r"```[\s\S]*?```", text):
        ranges.append((m.start(), m.end()))
    for m in re.finditer(r"(?:^\|.+\|\n?)+", text, re.MULTILINE):
        ranges.append((m.start(), m.end()))
    return sorted(ranges, key=lambda r: r[0])


def _is_inside_protected(pos: int, protected: list[tuple[int, int]]) -> bool:
    for start, end in protected:
        if start <= pos < end:
            return True
    return False


# ------------------------------------------------------------------ #
# 分块主逻辑
# ------------------------------------------------------------------ #
def split_text(
    text: str,
    filename: str,
    user_id: str,
    doc_id: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> list[Chunk]:
    if not text or not text.strip():
        logger.warning("[Chunking] 文本为空，跳过分块: %s", filename)
        return []

    _chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
    _chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
    _chunk_min = settings.RAG_CHUNK_MIN
    _doc_id = doc_id or _make_doc_id(filename, user_id)

    protected = _find_protected_ranges(text)

    # Step 1: 按 # / ## / ### 标题拆 section，保留标题层级
    sections = _split_by_headings(text, protected)

    # Step 2: 维护标题栈，每个 section 内按段落切到 chunk_size
    pieces: list[_Piece] = []
    heading_stack: list[tuple[int, str]] = []
    for level, heading, body in sections:
        _update_headings(heading_stack, level, heading)
        section_path = " > ".join(h for _, h in heading_stack)
        current_level = heading_stack[-1][0] if heading_stack else 0
        section_chunks = _chunk_section(body, _chunk_size, section_path)
        for chunk_text in section_chunks:
            pieces.append(
                _Piece(text=chunk_text, section_path=section_path, heading_level=current_level)
            )

    # Step 3: 短尾合并
    pieces = _merge_short_tail(pieces, _chunk_min, _chunk_size)

    # Step 4: 相邻重叠
    if _chunk_overlap > 0 and len(pieces) > 1:
        pieces = _add_overlap(pieces, _chunk_overlap)

    # Step 5: 长度安全切分（避免 Milvus VARCHAR 静默截断）
    pieces = _enforce_max_length(pieces, _MAX_SAFE_TEXT_LEN)

    # Step 5b: Milvus 硬上限兜底，确保绝不超 4096（_MAX_SAFE_TEXT_LEN 可能被误配）
    pieces = _enforce_max_length(pieces, _MILVUS_VARCHAR_MAX)

    # Step 6: 构建 Chunk 对象
    base_meta = extra_metadata or {}
    return [
        Chunk(
            text=p.text,
            chunk_index=i,
            doc_id=_doc_id,
            source=filename,
            user_id=user_id,
            metadata={
                **base_meta,
                "section_path": p.section_path,
                "heading_level": p.heading_level,
            },
        )
        for i, p in enumerate(pieces)
    ]


# ------------------------------------------------------------------ #
# 标题拆分
# ------------------------------------------------------------------ #
def _split_by_headings(
    text: str, protected: list[tuple[int, int]]
) -> list[tuple[int, str, str]]:
    """按 # / ## / ### 拆分，返回 [(level, heading, body), ...]。

    level=0 表示文档开头无标题部分。
    跳过 protected range（代码块、表格）内的伪标题。
    """
    pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    all_matches = list(pattern.finditer(text))
    matches = [m for m in all_matches if not _is_inside_protected(m.start(), protected)]

    if not matches:
        return [(0, "", text)]

    sections: list[tuple[int, str, str]] = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((level, heading, body))

    if matches[0].start() > 0:
        pre = text[: matches[0].start()].strip()
        if pre:
            sections.insert(0, (0, "", pre))

    return sections


def _update_headings(stack: list[tuple[int, str]], level: int, heading: str) -> None:
    """根据标题层级更新 breadcrumb 栈，使其反映真实的标题嵌套关系。"""
    if level <= 0 or not heading:
        return
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, heading))


# ------------------------------------------------------------------ #
# section 内分块
# ------------------------------------------------------------------ #
def _chunk_section(
    body: str,
    chunk_size: int,
    breadcrumb: str = "",
) -> list[str]:
    """将单个 section 的 body 切分为 chunk 列表，避免打断受保护区间。"""
    if not body:
        return []

    paragraphs = re.split(r"\n{2,}", body)
    section_protected = _find_protected_ranges(body)
    chunks: list[str] = []
    buffer = ""

    # 使用偏移量跟踪，避免重复文本导致 find() 返回错误位置
    current_offset = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 从 current_offset 开始查找，确保定位准确
        para_start_in_body = body.find(para, current_offset)
        if para_start_in_body < 0:
            para_start_in_body = current_offset

        # 更新偏移量到当前段落结束位置
        current_offset = para_start_in_body + len(para)

        # 判断段落是否在受保护区间内
        if para_start_in_body >= 0 and _is_inside_protected(
            para_start_in_body + len(para) // 2, section_protected
        ):
            pieces = [para]
        else:
            pieces = _split_long_paragraph(para, chunk_size)

        for piece in pieces:
            candidate = f"{buffer}\n\n{piece}" if buffer else piece
            prefix = f"{breadcrumb}\n\n" if breadcrumb and not chunks and not buffer else ""

            if len(prefix + candidate) <= chunk_size:
                buffer = candidate
            else:
                if buffer:
                    chunks.append(prefix + buffer if prefix else buffer)
                buffer = piece

    if buffer:
        prefix = f"{breadcrumb}\n\n" if breadcrumb and not chunks else ""
        chunks.append(prefix + buffer if prefix else buffer)

    return chunks


def _split_long_paragraph(para: str, chunk_size: int) -> list[str]:
    """超长段落按中英文句子分隔符切分。"""
    if len(para) <= chunk_size:
        return [para]

    sentences = re.split(r"(?<=[。！？.!?])\s*", para)
    pieces: list[str] = []
    buffer = ""

    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(buffer) + len(sentence) <= chunk_size:
            buffer = f"{buffer} {sentence}".strip() if buffer else sentence
        else:
            if buffer:
                pieces.append(buffer)
            buffer = sentence

    if buffer:
        pieces.append(buffer)

    result: list[str] = []
    for piece in pieces:
        if len(piece) <= chunk_size:
            result.append(piece)
        else:
            for i in range(0, len(piece), chunk_size):
                result.append(piece[i: i + chunk_size])
    return result


# ------------------------------------------------------------------ #
# 短尾合并 & 重叠
# ------------------------------------------------------------------ #
def _merge_short_tail(pieces: list[_Piece], min_size: int, max_size: int) -> list[_Piece]:
    """将最后一个过短 piece 合并到前一个（如果合并后不超过 max_size）。

    只在同 section 内合并：跨 section_path 的合并会破坏 breadcrumb 准确性，
    宁可保留一个短尾，也不混淆章节归属。
    """
    if len(pieces) < 2:
        return pieces

    last = pieces[-1]
    if len(last.text) >= min_size:
        return pieces

    prev = pieces[-2]
    if prev.section_path != last.section_path:
        return pieces

    if len(prev.text) + len(last.text) + 2 <= max_size:
        merged = pieces[:-2]
        merged.append(
            _Piece(
                text=f"{prev.text}\n\n{last.text}",
                section_path=prev.section_path,
                heading_level=prev.heading_level,
            )
        )
        return merged

    return pieces


def _add_overlap(pieces: list[_Piece], overlap: int) -> list[_Piece]:
    """在相邻 piece 之间添加重叠文本，保留各自的 section 上下文。"""
    if overlap <= 0:
        return pieces
    result: list[_Piece] = []
    for i, p in enumerate(pieces):
        if i == 0:
            result.append(p)
            continue
        prev_text = pieces[i - 1].text
        if len(prev_text) > overlap:
            new_text = prev_text[-overlap:] + "\n\n" + p.text
            result.append(
                _Piece(text=new_text, section_path=p.section_path, heading_level=p.heading_level)
            )
        else:
            result.append(p)
    return result


def _enforce_max_length(pieces: list[_Piece], max_len: int) -> list[_Piece]:
    """硬上限保护：超过 max_len 的 piece 按句子/换行边界切分，避免 Repository 静默截断。"""
    result: list[_Piece] = []
    for p in pieces:
        if len(p.text) <= max_len:
            result.append(p)
            continue
        for sub_text in _split_at_safe_boundary(p.text, max_len):
            result.append(
                _Piece(text=sub_text, section_path=p.section_path, heading_level=p.heading_level)
            )
    return result


def _split_at_safe_boundary(text: str, max_len: int) -> list[str]:
    """使用 LangChain 递归分割器按语义边界切分文本。"""
    if len(text) <= max_len:
        return [text]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_len,
        chunk_overlap=0,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ",", " ", ""],
        keep_separator=True,
    )
    return splitter.split_text(text)
