"""
Agent 工具适配层

将 Service 层能力暴露为 LLM 可调用的工具。
职责：
- 参数校验与预处理
- 调用 Service 层执行业务逻辑
- 记录 Agent 级别的调用日志
- 集中管理工具注册表 TOOLS
"""
import logging
from pathlib import Path
from typing import List, Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_community.tools import DuckDuckGoSearchResults

from app.services import memory_service
from app.services import rag_service
from app.tools.file_parser import parse_file_with_cache, get_parsed_pdf_path

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Memory 工具
# ------------------------------------------------------------------ #
MemoryCategory = Literal["preference", "progress", "fact", "goal"]


class MemoryFact(BaseModel):
    """一条需要保存的记忆事实"""
    user_quote: str = Field(description="用户原话精确引用，用于提取和保存记忆")
    category: Optional[MemoryCategory] = Field(
        default=None,
        description="记忆分类（仅允许：preference 偏好 / progress 进度 / fact 事实 / goal 目标）",
    )


class SaveMemoryInput(BaseModel):
    """将结构化记忆事实批量保存到用户的长期记忆中"""
    user_id: str = Field(description="用户唯一标识，用于隔离不同用户的记忆")
    facts: List[MemoryFact] = Field(description="需要保存的记忆事实列表，每条包含用户原话和可选分类")
    conversation_answer_summary: Optional[str] = Field(
        default=None, description="本次模型回复的总结，作为记忆上下文存入 metadata"
    )
    related_doc_id: Optional[str] = Field(
        default=None, description="当前讨论相关的 RAG 文档 doc_id（通过 list_knowledge_documents 获取），用于建立记忆与文档的关联"
    )
    related_doc_source: Optional[str] = Field(
        default=None, description="关联文档的原始文件名，与 related_doc_id 配合使用"
    )


@tool(args_schema=SaveMemoryInput)
def save_memory(
    user_id: str,
    facts: List[MemoryFact],
    conversation_answer_summary: Optional[str] = None,
    related_doc_id: Optional[str] = None,
    related_doc_source: Optional[str] = None,
) -> str:
    """将重要信息结构化保存到用户的长期记忆中。

    适合保存用户偏好、学习进度、重要结论等需要跨会话记住的内容。
    支持批量保存多条记忆事实，每条基于用户原话精确提取。
    当讨论围绕特定文档时，应传入 related_doc_id 和 related_doc_source 建立关联。
    """
    logger.info("[AgentTool] save_memory user=%s facts_count=%d doc_id=%s", user_id, len(facts), related_doc_id)
    return memory_service.save_memory(user_id, facts, conversation_answer_summary, related_doc_id, related_doc_source)


@tool
def delete_memory(memory_id: str, user_id: str) -> str:
    """删除指定的一条长期记忆。

    Args:
        memory_id: 记忆的唯一 ID，可通过 list_memories 或 search_memory 获取。
        user_id: 用户唯一标识。
    """
    logger.info("[AgentTool] delete_memory memory_id=%s user=%s", memory_id, user_id)
    return memory_service.delete_memory(memory_id, user_id)


@tool
def clear_memories(user_id: str) -> str:
    """清空用户的全部长期记忆（慎用）。

    Args:
        user_id: 用户唯一标识。
    """
    logger.info("[AgentTool] clear_memories user=%s", user_id)
    return memory_service.clear_memories(user_id)


@tool
def list_memories_by_doc(user_id: str, doc_id: str) -> str:
    """查询与指定 RAG 文档关联的所有长期记忆。

    当学生问"关于这份文档我记住了什么"或需要回顾文档学习记录时使用。
    返回该文档相关的所有记忆，包含记忆 ID、分类和内容。

    Args:
        user_id: 用户唯一标识。
        doc_id: 文档唯一 ID（通过 list_knowledge_documents 获取）。
    """
    logger.info("[AgentTool] list_memories_by_doc doc=%s user=%s", doc_id, user_id)
    return memory_service.list_memories_by_doc(user_id, doc_id)


@tool
def search_memory(query: str, user_id: str, top_k: int = 5) -> str:
    """从用户的长期记忆中检索与查询最相关的内容。

    Args:
        query: 检索查询，描述你想找的信息。
        user_id: 用户唯一标识。
        top_k: 返回最相关的记忆条数，默认 5。
    """
    logger.info("[AgentTool] search_memory user=%s", user_id)
    return memory_service.search_memory(query, user_id=user_id, top_k=top_k)


@tool
def list_memories(user_id: str) -> str:
    """列出用户的所有长期记忆（不经过向量检索，直接按 user_id 全量返回）。

    Args:
        user_id: 用户唯一标识。
    """
    logger.info("[AgentTool] list_memories user=%s", user_id)
    return memory_service.list_memories(user_id)


# ------------------------------------------------------------------ #
# RAG 知识库工具
# ------------------------------------------------------------------ #
@tool
def ingest_document(file_path: str, user_id: str, replace: bool = True, force: bool = False) -> str:
    """将本地文件以"增量入库"方式持久化到 RAG 知识库（支持 PDF / TXT / MD / DOCX）。

    解析文件内容 → 文本分块 → 向量化 → 存入 Milvus 知识库。
    内容相同的 chunk 不会重复 embedding，内容修改的 chunk 会替换旧版本。

    Args:
        file_path: 文件的绝对路径或虚拟路径（如 /uploads/xxx.pdf）。
        user_id: 用户唯一标识，用于数据隔离。
        replace: True（默认）= 完整替换，旧文件中未出现在新文件的 chunk 会被删除；
                 False = 只更新传入的部分，保留旧文件中未被覆盖的 chunk。
                 当不确定是否上传了完整文件时，可用 replace=False 避免误删。
        force: 为 True 时跳过 shrink_ratio 完整性校验，允许强制覆盖。
               仅在上传文件明显变小时需要设为 True。
    """
    logger.info("[AgentTool] ingest_document file=%s user=%s replace=%s force=%s", file_path, user_id, replace, force)

    # 虚拟路径映射：/uploads/foo.pdf → 物理 workspace/uploads/foo.pdf
    if file_path.startswith("/"):
        workspace_dir = Path(__file__).resolve().parents[1] / "workspace"
        path = str((workspace_dir / file_path.lstrip("/")).resolve())
    else:
        path = file_path

    return rag_service.ingest_document(path, user_id, replace=replace, force=force)


@tool
def search_knowledge(query: str, user_id: str, top_k: int = 5) -> str:
    """从 RAG 知识库中混合检索与问题最相关的文档片段。

    检索链路：dense (qwen3-embedding) ANN + sparse (Milvus BM25) → RRF 融合。
    Hybrid 失败时会降级为 dense-only，并在返回结果中明确提示。

    适合回答"文档里说了什么"类问题，与 search_memory 互补：
    - search_memory：检索用户个人记忆（偏好、进度、结论）
    - search_knowledge：检索用户上传的文档内容

    Args:
        query: 检索查询（自然语言描述你想找的信息）。
        user_id: 用户唯一标识。
        top_k: 返回最相关的片段数，默认 5。
    """
    logger.info("[AgentTool] search_knowledge user=%s", user_id)
    return rag_service.search_knowledge(query, user_id, top_k)


@tool
def list_knowledge_documents(user_id: str) -> str:
    """列出用户已入库到 RAG 知识库的所有文档。

    返回文件名、片段数量、入库时间和 doc_id，可用于后续删除操作。

    Args:
        user_id: 用户唯一标识。
    """
    logger.info("[AgentTool] list_knowledge_documents user=%s", user_id)
    return rag_service.list_documents(user_id)


@tool
def delete_knowledge_document(doc_id: str, user_id: str) -> str:
    """从 RAG 知识库中删除指定文档的所有片段。

    doc_id 可通过 list_knowledge_documents 工具获取。

    Args:
        doc_id: 文档唯一 ID。
        user_id: 用户唯一标识（防止跨用户误删）。
    """
    logger.info("[AgentTool] delete_knowledge_document doc=%s user=%s", doc_id, user_id)
    return rag_service.delete_document(doc_id, user_id)


# ------------------------------------------------------------------ #
# 联网搜索工具
# ------------------------------------------------------------------ #
@tool
def web_search(query: str) -> str:
    """使用 DuckDuckGo 搜索互联网信息。

    适合获取实时信息、查询最新新闻、验证事实、查找公开资料等需要联网的场景。
    与 search_knowledge（检索用户私有知识库）互补：
    - web_search：检索公开互联网信息
    - search_knowledge：检索用户上传的私有文档

    Args:
        query: 搜索查询词（自然语言描述你想查找的信息）。
    """
    logger.info("[AgentTool] web_search query=%s", query)
    try:
        search = DuckDuckGoSearchResults(max_results=5)
        return search.run(query)
    except Exception as e:
        logger.error("[web_search] 失败: %s", e)
        return f"搜索失败：{e}"


# ------------------------------------------------------------------ #
# PDF 工具
# ------------------------------------------------------------------ #
@tool
def parse_pdf(file_path: str) -> str:
    """解析指定路径的 PDF 文件，提取文本内容供智能体参考。

    解析结果会自动缓存到本地。如需将内容入库到知识库，请使用 ingest_document。

    Args:
        file_path: PDF 文件的绝对路径或虚拟路径（如 /uploads/xxx.pdf）。
    """
    logger.info("[AgentTool] parse_pdf file=%s", file_path)

    # 虚拟路径映射：/uploads/foo.pdf → 物理 workspace/uploads/foo.pdf
    if file_path.startswith("/"):
        workspace_dir = Path(__file__).resolve().parents[1] / "workspace"
        path = (workspace_dir / file_path.lstrip("/")).resolve()
    else:
        path = Path(file_path).resolve()

    if not path.suffix.lower() == ".pdf":
        return f"错误：仅支持 PDF 文件，当前后缀为 {path.suffix}"

    result = parse_file_with_cache(str(path))
    if not result.success:
        return f"PDF 解析失败：{result.error}"

    text = result.text
    cache_path = get_parsed_pdf_path(str(path))

    # 构建摘要（前 3000 字符）
    max_summary = 3000
    if len(text) <= max_summary:
        summary = text
    else:
        summary = text[:max_summary] + f"\n\n...（共 {len(text)} 字符，已截断）"

    return (
        f"PDF 已解析，完整文本已保存到：{cache_path}\n"
        f"如需入库到知识库，请使用 ingest_document 工具。\n\n"
        f"--- 内容摘要 ---\n{summary}"
    )


# ------------------------------------------------------------------ #
# 工作目录工具
# ------------------------------------------------------------------ #
@tool
def get_working_directory() -> str:
    """返回工作区的根目录路径。

    Agent 的所有文件操作（上传、解析、生成报告）都以该目录为根。
    子目录说明：uploads/ 用户上传文件、parsed/ 解析缓存、report/ 生成的报告、skills/ 技能脚本。
    """
    workspace_dir = Path(__file__).resolve().parents[1] / "workspace"
    return str(workspace_dir.resolve())


# ------------------------------------------------------------------ #
# 工具注册表
# ------------------------------------------------------------------ #
TOOLS = [
    parse_pdf,
    save_memory,
    search_memory,
    list_memories,
    list_memories_by_doc,
    delete_memory,
    clear_memories,
    ingest_document,
    search_knowledge,
    list_knowledge_documents,
    delete_knowledge_document,
    web_search,
    get_working_directory,
]
