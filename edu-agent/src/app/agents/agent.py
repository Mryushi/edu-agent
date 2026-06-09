"""
智能对话Agent系统
"""
from dataclasses import dataclass
from pathlib import Path

from deepagents import create_deep_agent as create_agent
from deepagents.backends import FilesystemBackend, LocalShellBackend, CompositeBackend
from deepagents.middleware import SkillsMiddleware
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from app.core.llms import image_llm_model, text_model
from app.middleware.pdf_context import PDFContextMiddleware
from app.agents.tools import TOOLS
from app.agents.mcp_tools import get_mcp_tools_cached


@dataclass
class AgentContext:
    """运行时上下文，从 config.configurable 自动填充。"""
    user_id: str = "default"

_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "system_prompt.md"
SYSTEM_PROMPT = _PROMPT_FILE.read_text(encoding="utf-8")

def _has_image_in_messages(request: ModelRequest) -> bool:
    """
    遍历 request.messages，检测 HumanMessage 的 content 列表中是否存在图片 block。

    实际图片 block 格式（前端传入）：
        {
            "type": "image",
            "data": "/9j/4AAQ...",          # base64 编码的图片数据
            "mimeType": "image/png",         # MIME 类型
            "metadata": {"name": "login.png"} # 可选元数据
        }

    同时兼容 OpenAI image_url 格式：
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    """
    for message in request.messages:
        content = message.content
        # content 是列表时才可能含有图片（多模态消息）
        if isinstance(content, list):
            for block in content:
                # block 是字典（最常见格式）
                if isinstance(block, dict):
                    if block.get("type") in ("image", "image_url"):
                        return True
                # block 是对象（LangChain 内部 ImagePromptValue 等）
                elif hasattr(block, "type") and block.type in ("image", "image_url"):
                    return True
    return False

@wrap_model_call
async def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """
    根据对话消息中是否含有图片，动态切换底层模型：
      - 含有图片 → image_llm_model（豆包多模态视觉模型，支持图文理解）
      - 纯文本   → deepseek_model（DeepSeek Chat，成本更低、速度更快）

    使用 async 定义以兼容异步上下文（ainvoke / astream）。
    """
    if _has_image_in_messages(request):
        # 消息中含有图片，切换为多模态视觉模型
        model = image_llm_model
    else:
        # 纯文本对话，使用 DeepSeek 文本模型
        model = text_model

    return await handler(request.override(model=model))


mcp_tools = get_mcp_tools_cached()
tools = TOOLS + mcp_tools

workspace_dir = Path(__file__).resolve().parents[1] / "workspace"

file_backend = FilesystemBackend(root_dir=workspace_dir, virtual_mode=True)
skills_middleware = SkillsMiddleware(backend=file_backend, sources=["/skills/"])

shell_backend = LocalShellBackend(
    root_dir=workspace_dir,
    inherit_env=True,
    virtual_mode=True,
)
composite_backend = CompositeBackend(
    default=shell_backend,  # 默认使用 shell 执行命令
    routes={
        "/": file_backend,
    },
)

agent = create_agent(
    model=text_model,
    tools=tools,
    memory=["/memories/memory.md"],
    middleware=[
        skills_middleware,
        dynamic_model_selection,
        PDFContextMiddleware(),
    ],
    backend=composite_backend,
    system_prompt=SYSTEM_PROMPT,
    context_schema=AgentContext,

)
