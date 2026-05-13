"""
统一文件解析器

- PyMuPDF 原生格式（PDF/XPS/EPUB/MOBI/FB2/CBZ/SVG/图片）→ PyMuPDF4LLMLoader，输出 Markdown
- 纯文本（TXT/MD/HTML/XML/JSON 等）→ 直接读取
- DOCX → python-docx（PyMuPDF Pro 才原生支持 DOCX）
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# PyMuPDF 原生支持的文档/图片格式
_PYMUPDF_EXTENSIONS = {
    ".pdf", ".xps", ".epub", ".mobi", ".fb2", ".cbz", ".svg",
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff",
    ".pnm", ".pgm", ".pbm", ".ppm", ".pam", ".psd",
}
# 纯文本格式（直接读取）
_TEXT_EXTENSIONS = {".txt", ".md", ".html", ".xml", ".json", ".csv", ".py", ".js", ".ts"}

SUPPORTED_EXTENSIONS = _PYMUPDF_EXTENSIONS | _TEXT_EXTENSIONS | {".doc", ".docx"}


@dataclass
class ParseResult:
    """文件解析结果"""
    text: str                          # 提取的纯文本
    filename: str                      # 原始文件名
    extension: str                     # 文件后缀（小写）
    file_size: int                     # 文件大小（字节）
    parsed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    page_count: Optional[int] = None   # 页数（PDF 有效）
    error: Optional[str] = None        # 解析失败时的错误信息

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text)


def _parse_with_pymupdf(file_path: str) -> str:
    """用 PyMuPDF4LLMLoader 解析 PDF/XPS/EPUB/图片等，输出 Markdown 文本。"""
    from langchain_pymupdf4llm import PyMuPDF4LLMLoader
    docs = PyMuPDF4LLMLoader(file_path).load()
    return "\n\n".join(d.page_content for d in docs)


def _parse_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _word_to_pdf(file_path: str) -> str:
    """用 LibreOffice 将 DOC/DOCX 转为 PDF，返回生成的 PDF 路径。"""
    import subprocess
    import tempfile
    out_dir = tempfile.mkdtemp()
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, file_path],
        check=True, capture_output=True,
    )
    stem = Path(file_path).stem
    pdf_path = os.path.join(out_dir, f"{stem}.pdf")
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"LibreOffice 转换失败，未找到输出文件: {pdf_path}")
    return pdf_path


def _parse_docx(file_path: str) -> str:
    """DOC/DOCX → PDF（LibreOffice）→ PyMuPDF4LLMLoader。"""
    pdf_path = _word_to_pdf(file_path)
    try:
        return _parse_with_pymupdf(pdf_path)
    finally:
        try:
            os.unlink(pdf_path)
            os.rmdir(os.path.dirname(pdf_path))
        except OSError:
            pass


def parse_file(file_path: str) -> ParseResult:
    """
    解析本地文件，返回 ParseResult。

    Args:
        file_path: 文件的绝对路径或相对路径。

    Returns:
        ParseResult，包含提取文本和元数据。
    """
    path = Path(file_path).resolve()
    filename = path.name
    ext = path.suffix.lower()

    if not path.exists():
        return ParseResult(text="", filename=filename, extension=ext,
                           file_size=0, error=f"文件不存在: {file_path}")

    if ext not in SUPPORTED_EXTENSIONS:
        return ParseResult(text="", filename=filename, extension=ext,
                           file_size=path.stat().st_size,
                           error=f"不支持的文件格式: {ext}，支持: {', '.join(SUPPORTED_EXTENSIONS)}")

    file_size = path.stat().st_size
    logger.info("[FileParser] 开始解析: %s (%d bytes)", filename, file_size)

    try:
        if ext in _PYMUPDF_EXTENSIONS:
            text = _parse_with_pymupdf(str(path))
        elif ext in (".doc", ".docx"):
            text = _parse_docx(str(path))
        else:
            text = _parse_txt(str(path))

        logger.info("[FileParser] 解析完成: %s，文本长度: %d", filename, len(text))
        return ParseResult(text=text, filename=filename, extension=ext, file_size=file_size)

    except Exception as e:
        logger.error("[FileParser] 解析失败: %s -> %s", filename, e)
        return ParseResult(text="", filename=filename, extension=ext,
                           file_size=file_size, error=str(e))


def parse_bytes(data: bytes, filename: str) -> ParseResult:
    """
    从字节数据解析文件（适用于上传场景，无需先落盘）。
    内部会写临时文件再解析，解析完毕后删除。

    Args:
        data: 文件字节数据。
        filename: 原始文件名（用于判断格式）。
    """
    import tempfile
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return ParseResult(text="", filename=filename, extension=ext,
                           file_size=len(data),
                           error=f"不支持的文件格式: {ext}")

    suffix = ext
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        result = parse_file(tmp_path)
        # 用原始文件名覆盖临时文件名
        result.filename = filename
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
