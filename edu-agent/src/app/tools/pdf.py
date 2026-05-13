# PDF 处理器
"""
PDF 文档处理器，支持文本提取和缓存
"""
from app.core.config import settings

# uv pip install langchain-community langchain-pymupdf4llm

import tempfile
import os
import logging
import hashlib
import time
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders.parsers import LLMImageBlobParser
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from app.core.llms import image_llm_model

logger = logging.getLogger(__name__)

# PDF 内容缓存，避免重复解析同一个文件
_pdf_cache: dict[str, str] = {}

# 解析结果持久化缓存目录
_PARSED_DIR = Path(__file__).resolve().parent.parent / "workspace" / "parsed"
_PARSED_DIR.mkdir(parents=True, exist_ok=True)


def _safe_delete_temp_file(file_path: str, max_retries: int = 3, delay: float = 0.1) -> None:
    """
    安全删除临时文件，处理Windows文件锁定问题

    Args:
        file_path: 要删除的文件路径
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    if not os.path.exists(file_path):
        return

    for attempt in range(max_retries):
        try:
            os.unlink(file_path)
            logger.debug(f"临时文件已删除: {file_path}")
            return
        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.debug(f"删除临时文件失败（尝试 {attempt + 1}/{max_retries}），等待后重试: {e}")
                time.sleep(delay)
            else:
                logger.warning(f"无法删除临时文件（已重试{max_retries}次），文件将由系统清理: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件时发生异常: {e}")
            break


def _get_cache_key(data: bytes, filename: str) -> str:
    """生成PDF数据的缓存键"""
    pdf_hash = hashlib.md5(data).hexdigest()
    return f"{filename}_{pdf_hash}"


def get_parsed_pdf_path(file_path: str) -> Path:
    """
    根据原 PDF 文件路径生成解析结果缓存文件路径。

    缓存键基于文件路径 + 修改时间，确保 PDF 更新后缓存自动失效。
    """
    path = Path(file_path).resolve()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0
    cache_key = hashlib.md5(f"{path}:{mtime}".encode()).hexdigest()[:16]
    return _PARSED_DIR / f"{path.stem}_{cache_key}.md"


def _create_loader(file_path: str) -> PyMuPDF4LLMLoader:
    """
    根据全局配置创建 PyMuPDF4LLMLoader

    Args:
        file_path: PDF 文件路径

    Returns:
        配置好的 PyMuPDF4LLMLoader 实例
    """
    logger.info(f"使用 PyMuPDF4LLM 解析PDF: {file_path}")
    if settings.ENABLE_PDF_MULTIMODAL:
        image_parser = LLMImageBlobParser(
            model=image_llm_model,
            prompt=settings.IMAGE_PARSER_PROMPT,
        )
        return PyMuPDF4LLMLoader(
            file_path,
            mode="single",
            extract_images=True,
            images_parser=image_parser,
            table_strategy="lines"
        )
    else:
        return PyMuPDF4LLMLoader(
            file_path,
            mode="single",
            table_strategy="lines"
        )


def _extract_text_from_loader(loader: PyMuPDF4LLMLoader) -> str:
    """
    从 Loader 加载文档并提取文本内容

    Args:
        loader: 已配置的 PyMuPDF4LLMLoader 实例

    Returns:
        提取的文本内容
    """
    documents = loader.load()
    if documents:
        text_content = documents[0].page_content
        logger.info(f"PyMuPDF4LLM 解析成功，内容长度: {len(text_content)} 字符")
        return text_content
    return "PDF文件解析后内容为空"


def _write_temp_pdf(pdf_data: bytes) -> str:
    """
    将 PDF 字节数据写入临时文件，返回临时文件路径

    Args:
        pdf_data: PDF 文件字节数据

    Returns:
        临时文件绝对路径
    """
    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    try:
        temp_file.write(pdf_data)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        return temp_file.name
    finally:
        temp_file.close()


def extract_pdf_text(pdf_data: bytes, filename: str = "unknown.pdf", cache: Optional[dict] = None) -> str:
    """
    从PDF字节数据中提取文本，使用缓存避免重复解析

    提取的方法：
    1、langchain pdf加载器：https://docs.langchain.com/oss/python/integrations/document_loaders/index#pdfs
        推荐 pip install -qU langchain-community langchain-pymupdf4llm，支持基于多模态大模型进行图片解析
    2、DeepSeek ocr大模型
    3、PaddleOCR VL 0.9B（推荐）--部署需要GPU
        推荐 https://www.paddleocr.ai/latest/version3.x/pipeline_usage/PaddleOCR-VL.html

    Args:
        pdf_data: PDF 文件字节数据
        filename: 文件名，用于日志和缓存键
        cache: 可选的外部缓存字典

    Returns:
        提取的文本内容
    """
    cache_key = _get_cache_key(pdf_data, filename)

    # 检查缓存
    if cache is not None and cache_key in cache:
        logger.info(f"从缓存中获取PDF内容: {filename}")
        return cache[cache_key]

    temp_file_path = _write_temp_pdf(pdf_data)

    try:
        loader = _create_loader(temp_file_path)
        text_content = _extract_text_from_loader(loader)

        # 缓存结果
        if cache is not None:
            cache[cache_key] = text_content
            logger.info(f"PDF内容已缓存: {filename}")

        return text_content
    except Exception as e:
        logger.error(f"PDF文本提取失败: {e}")
        return f"PDF文件处理出错: {str(e)}"
    finally:
        _safe_delete_temp_file(temp_file_path)


def extract_pdf_text_from_file(file_path: str, cache: Optional[dict] = None) -> str:
    """
    从PDF文件路径中提取文本，使用文件级缓存避免重复解析。

    Args:
        file_path: PDF 文件的绝对路径或相对路径
        cache: 可选的外部内存缓存字典（保留向后兼容）

    Returns:
        提取的文本内容
    """
    if not os.path.isfile(file_path):
        logger.error("PDF文件不存在: %s", file_path)
        return f"PDF文件不存在: {file_path}"

    # 1. 检查文件级持久化缓存
    cache_path = get_parsed_pdf_path(file_path)
    if cache_path.exists():
        logger.info("从文件缓存读取PDF: %s -> %s", file_path, cache_path)
        try:
            return cache_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("读取PDF缓存文件失败: %s", e)

    # 2. 检查内存缓存（向后兼容）
    try:
        with open(file_path, "rb") as f:
            pdf_data = f.read()
    except OSError as e:
        logger.error("读取PDF文件失败: %s", e)
        return f"读取PDF文件失败: {str(e)}"

    filename = os.path.basename(file_path)
    cache_key = _get_cache_key(pdf_data, filename)
    if cache is not None and cache_key in cache:
        logger.info("从内存缓存中获取PDF内容: %s", file_path)
        return cache[cache_key]

    # 3. 解析PDF
    try:
        loader = _create_loader(file_path)
        text_content = _extract_text_from_loader(loader)
    except Exception as e:
        logger.error("PDF文本提取失败: %s", e)
        return f"PDF文件处理出错: {str(e)}"

    # 4. 保存到文件缓存
    try:
        cache_path.write_text(text_content, encoding="utf-8")
        logger.info("PDF解析结果已缓存: %s", cache_path)
    except Exception as e:
        logger.warning("PDF缓存写入失败: %s", e)

    # 5. 保存到内存缓存（向后兼容）
    if cache is not None:
        cache[cache_key] = text_content

    return text_content
