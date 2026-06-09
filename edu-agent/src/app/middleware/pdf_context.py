"""
PDF 上下文注入中间件 (PDFContextMiddleware)

从 messages 中最后一个用户消息的 additional_kwargs.attachments 中提取 PDF，
将 base64 数据保存到本地 workspace/uploads/ 目录，并在该 HumanMessage 中追加提示，
通知智能体调用 parse_pdf 工具解析文件获取上下文。

支持多文件上传：遍历全部 PDF 附件，逐个保存后统一追加提示。
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Callable, Awaitable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.agents.middleware.types import ResponseT
from langchain_core.messages import HumanMessage
from langgraph.typing import ContextT

logger = logging.getLogger(__name__)

# PDF 临时保存目录（相对于本文件 ../../workspace/uploads）
_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "workspace" / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _decode_base64(data: str) -> bytes:
    """将 base64 字符串解码为 bytes。"""
    if "," in data:
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


class PDFContextMiddleware(AgentMiddleware):
    """PDF 文档上下文注入中间件。

    核心逻辑：
    1. 扫描最后一条用户消息，提取全部 PDF 附件。
    2. 将 base64 PDF 数据解码并保存到 workspace/uploads/ 目录（自动处理重名）。
    3. 在 HumanMessage 中追加提示文本，告知智能体文件列表及对应工具。
    """

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> Any:
        if not request.messages:
            return await handler(request)

        last_msg = request.messages[-1]
        if not isinstance(last_msg, HumanMessage):
            return await handler(request)

        pdf_list = self._extract_pdfs_from_message(last_msg)
        if not pdf_list:
            return await handler(request)

        saved_files: list[tuple[str, str]] = []
        for pdf_bytes, filename in pdf_list:
            safe_name = Path(filename).name
            file_path = _UPLOAD_DIR / safe_name

            # 处理重名：已存在则加序号后缀
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = _UPLOAD_DIR / f"{stem}_{counter}{suffix}"
                counter += 1

            try:
                file_path.write_bytes(pdf_bytes)
                # 传虚拟路径（/uploads/xxx.pdf），而非物理绝对路径
                # parse_pdf / ingest_document 会自动将虚拟路径映射到 workspace 目录
                virtual_path = f"/uploads/{file_path.name}"
                saved_files.append((filename, virtual_path))
                logger.info("[PDFContextMiddleware] PDF 已保存: %s (虚拟路径: %s)", file_path, virtual_path)
            except Exception as e:
                logger.warning("[PDFContextMiddleware] PDF 保存失败: %s", e)

        if not saved_files:
            return await handler(request)

        # 构建提示文本
        prompt_text = self._build_prompt(saved_files)

        # 构造新的 HumanMessage，追加提示
        original_content = last_msg.content
        if isinstance(original_content, str):
            new_content = original_content + prompt_text
        elif isinstance(original_content, list):
            new_content = list(original_content) + [{"type": "text", "text": prompt_text}]
        else:
            new_content = str(original_content) + prompt_text

        new_msg = HumanMessage(
            content=new_content,
            additional_kwargs=last_msg.additional_kwargs,
        )

        new_messages = list(request.messages[:-1]) + [new_msg]
        request = request.override(messages=new_messages)

        return await handler(request)

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    def _extract_pdfs_from_message(self, msg: HumanMessage) -> list[tuple[bytes, str]]:
        """从消息附件中提取所有 PDF，返回 (bytes, filename) 列表。"""
        attachments = msg.additional_kwargs.get("attachments", [])
        if not isinstance(attachments, list):
            return []

        pdfs: list[tuple[bytes, str]] = []
        for att in attachments:
            if not isinstance(att, dict):
                continue
            if att.get("mimeType", "").lower() != "application/pdf":
                continue

            data = att.get("data")
            if not data or not isinstance(data, str):
                continue

            try:
                pdf_bytes = _decode_base64(data)
                filename = att.get("metadata", {}).get("filename", "document.pdf")
                pdfs.append((pdf_bytes, filename))
            except Exception as e:
                logger.warning("[PDFContextMiddleware] PDF 解码失败: %s", e)
                continue

        return pdfs

    @staticmethod
    def _build_prompt(saved_files: list[tuple[str, str]]) -> str:
        """根据保存的文件列表构建系统提示文本。

        职责：仅通知 LLM 有文件上传及保存路径，不指定具体工具。
        工具选择策略由 SYSTEM_PROMPT 统一管控。
        """
        if len(saved_files) == 1:
            filename, path = saved_files[0]
            return (
                f"\n\n[系统提示] 用户上传了 PDF 文件 '{filename}'，"
                f"保存在 '{path}'。"
            )

        lines = "\n".join(f"- {name}（{path}）" for name, path in saved_files)
        return (
            f"\n\n[系统提示] 用户上传了 {len(saved_files)} 个 PDF 文件：\n"
            f"{lines}"
        )
