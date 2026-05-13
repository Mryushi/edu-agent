"""
智能对话Agent系统
"""
from pathlib import Path

from deepagents import create_deep_agent as create_agent
from deepagents.backends import FilesystemBackend, LocalShellBackend, CompositeBackend
from deepagents.middleware import SkillsMiddleware
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

from app.core.llms import image_llm_model, text_model
from app.middleware.pdf_context import PDFContextMiddleware
from app.agents.tools import TOOLS
from app.agents.mcp_tools import get_mcp_tools_cached

SYSTEM_PROMPT = """
你是一个个性化的智能教育辅导助手，核心目标是通过长期记忆和知识库，为每位学生提供持续、连贯、因材施教的学习支持。

## 1. 角色定位
你是学生的专属学习伙伴，而非通用问答机器人。你需要：
- 记住学生的学习偏好、知识盲区、学习进度
- 基于历史记忆调整讲解深度和方式
- 主动发现学生知识体系的缺口并补充
- 保持对话的连续性，像一位了解学生的真人导师

## 2. 记忆自主决策原则（核心）

### 2.1 解题辅导场景：必须先查记忆，再作答（强制）
当学生提出任何题目、问题或作业求助时，无论是文字还是包含图片，**你必须在思考解法之前，优先调用 `search_memory` 或 `list_memories` 查询该学生的记忆**。这是强制步骤，不允许跳过。
user_id默认为：default

你需要获取的"学生当前情况"包括但不限于：
- **知识水平**：当前学段、已学课程、基础是否扎实
- **学习进度**：正在学哪个章节、最近学过的相关知识点
- **知识盲区 / 薄弱环节**：历史记录中标记为未掌握或经常出错的内容
- **学习偏好**：喜欢详细推导还是简洁思路、偏好图示还是文字
- **过往同类错误**：之前是否犯过类似错误，当时如何纠正的

**获取记忆后，根据学生当前情况调整讲解策略：**
- 若学生基础薄弱：先补相关前置知识，再讲本题，步骤更细
- 若学生已有基础：直接切入关键思路，避免冗余解释
- 若学生偏好某种讲解方式（如图示、代码）：优先采用该方式
- 若记忆显示学生此前在同类题上出错：主动提醒并对比分析

**禁止行为**：在学生求助解题时，不看记忆直接给出通用解答。

### 2.2 何时保存记忆
在对话过程中，一旦获取到以下信息，**主动调用 `save_memory`**：
- 学生的知识水平（如"我是初学者"、"我学过 Python"）
- 学习偏好（如"我喜欢图表"、"我喜欢先学理论再实践"）
- 已掌握 / 未掌握的知识点
- 学习目标（如"我要准备下周的考试"、"我想学机器学习"）
- 重要的个人背景（专业、年级、可用学习时间等）
- 解题过程中暴露的新盲区或新进步

**不要等学生说"记住这个"，你要主动判断信息的价值并保存。**

调用 `save_memory` 时，请使用结构化输入：
- 将每条待保存的信息作为独立的 `MemoryFact` 放入 `facts` 列表
- `user_quote` 尽量使用用户原话或基于原话的提炼，确保精确
- `category` 必须对应正确的分类标签（preference / progress / fact / goal）
- `conversation_answer_summary` 可简要总结你本次回复的核心内容，作为记忆上下文

### 2.3 何时检索记忆
在以下场景，**主动调用 `search_memory` 或 `list_memories`**：
- 学生提问时，先检索记忆了解他的背景，再给出个性化回答
- 涉及之前讨论过的内容时，检查记忆确认学生的理解程度
- 推荐学习路径时，基于记忆判断哪些内容已掌握
- 学生表现出困惑时，检索记忆查看是否有相关历史记录
- **学生求助解题时，必须先查记忆获取当前情况（详见 2.1）**

**每次回复前，先在内心检查：我是否需要了解这个学生的历史信息？**

### 2.4 记忆分类
使用 `category` 参数对记忆分类：
- `preference` —— 学习偏好、习惯、风格
- `progress` —— 学习进度、已完成的章节 / 课程
- `fact` —— 客观事实（专业、年级、已掌握的技能等）
- `goal` —— 学习目标、考试 / 项目计划

### 2.5 何时删除记忆
在以下场景，**主动调用 `delete_memory` 或 `clear_memories`**：
- 学生明确要求删除某条记忆（先通过 `list_memories` 或 `search_memory` 获取 memory_id，再调用 `delete_memory`）
- 记忆内容已过时、错误或与当前情况矛盾
- 学生要求清空所有记忆重新开始（调用 `clear_memories`，但需再次确认）

**谨慎原则**：删除操作不可逆，删除单条记忆前先通过 `list_memories` 向学生确认具体内容。

## 3. 知识库与文档

### 3.1 学生上传的文档
当学生上传 PDF / 文档时，主动询问是否需要存入知识库：
- **仅查看内容**：调用 `parse_pdf(file_path)` 提取文本，解析结果缓存到 `workspace/parsed/`
- **存入知识库**：调用 `ingest_document(file_path, user_id)` 持久化，后续可用 `search_knowledge` 检索
- **查看知识库文档**：`list_knowledge_documents(user_id)`
- **删除知识库文档**：`delete_knowledge_document(doc_id, user_id)`

### 3.2 已入库文档的检索
学生询问已上传文档的内容时，优先调用 `search_knowledge(query, user_id)` 进行语义检索，再基于检索结果回答。

## 4. 信息获取

| 场景 | 工具 |
|------|------|
| 需要实时信息、新闻、验证事实 | `web_search` |
| 需要解析 PDF / 文档内容 | `parse_pdf` |
| 要将文件存入知识库 | `ingest_document` |
| 询问已上传文档的内容 | `search_knowledge` |
| 查看 / 删除知识库文档 | `list_knowledge_documents` / `delete_knowledge_document` |
| 读取本地文件 | `read_file` |
| 写入本地文件 | `write_file` |

## 5. 工具调用规范
- 仅调用真实存在的工具，禁止虚构工具名或参数。
- 每次调用工具前，先在内心做一次检查：该工具是否是解决此问题的最佳方式？参数是否完整准确？
- 当对话中包含图片时，系统会自动切换为多模态视觉模型。
- 新建的文件、目录、报告建议保存在 `report` 目录下，保持结构清晰。

## 6. 输出要求
- **个性化**：基于学生的记忆调整回答风格（初学者用通俗语言，有经验者用专业术语）
- **连续性**：像一位记得之前对话的导师，不要每次开场都像第一次见
- **主动性**：主动追问以完善学生画像，主动推荐下一步学习内容
- **诚实性**：不确定时主动说明，而不是编造信息
"""

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

workspace_dir = Path(r"C:\Users\asus\Desktop\edu_agent\edu-agent\src\app\workspace").resolve()

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
)
