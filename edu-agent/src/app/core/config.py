import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings

# 项目根目录（config.py 所在的 src/app/core/ 上三级）
_ROOT_DIR = Path(__file__).resolve().parents[3]
_ENV_FILE = _ROOT_DIR / ".env"

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ================================================
    # LLM 主文本模型
    # ================================================
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str

    # ================================================
    # Vision 视觉/多模态模型
    # ================================================
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str

    # ================================================
    # PDF 多模态解析
    # ================================================
    ENABLE_PDF_MULTIMODAL: bool
    IMAGE_PARSER_PROMPT: str = """你是一个专业的文档图像解析助手。请将图像内容完整转换为结构化文本：

## 任务要求
1. **文字提取**：完整提取所有可见文本，包括标题、正文、注释、页眉页脚
2. **结构还原**：保留原始层级关系（章节、列表、表格、代码块）
3. **视觉描述**：对图表、流程图、截图等补充必要的视觉说明
4. **语义标注**：标注关键信息（如字段名、按钮标签、错误提示等）

## 输出格式
- 使用标准 Markdown 格式
- 表格用 | 分隔，代码块标注语言类型
- 无需解释性文字，直接输出内容
- 开头和结尾不要添加 ```markdown 标记"""

    # ================================================
    # Milvus 向量数据库
    # ================================================
    MILVUS_URL: str
    MILVUS_TOKEN: Optional[str] = None   # 可选，本地无鉴权时留空
    MILVUS_DB_NAME: Optional[str] = None # 可选，使用默认 db 时留空
    MILVUS_METRIC_TYPE: str

    # ================================================
    # RAG 知识库配置
    # ================================================
    MILVUS_RAG_COLLECTION: str = "edu_agent_rag"

    # 分块参数
    RAG_CHUNK_SIZE: int
    RAG_CHUNK_OVERLAP: int
    RAG_CHUNK_MIN: int
    RAG_CHUNK_MAX_LEN: int

    # 检索参数
    RAG_TOP_K: int
    RAG_HYBRID_FETCH_K: int

    # ================================================
    # 嵌入模型配置（RAG 和 mem0 共用）
    # ================================================
    # 嵌入模型提供商：ollama 或 openai
    EMBEDDING_PROVIDER: str

    # Ollama 嵌入配置（当 EMBEDDING_PROVIDER=ollama 时使用）
    EMBEDDING_MODEL: str
    EMBEDDING_DIMS: int

    # OpenAI 兼容接口嵌入配置（当 EMBEDDING_PROVIDER=openai 时使用）
    OPENAI_EMBEDDING_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_BASE_URL: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: Optional[str] = None
    OPENAI_EMBEDDING_DIMS: Optional[int] = None  # 覆盖 EMBEDDING_DIMS

    # Ollama 服务地址
    OLLAMA_BASE_URL: str

    # ================================================
    # mem0 记忆系统配置
    # ================================================
    MEM0_COLLECTION: str = "edu_agent_memory"

    # ================================================
    # MCP 工具配置（可选）
    # ================================================
    MCP_SERVERS_JSON: Optional[str] = None

    # ================================================
    # 日志配置
    # ================================================
    LOG_LEVEL: str

    class Config:
        case_sensitive = True
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_mem0_config(self) -> Dict[str, Any]:
        """获取 mem0 配置（复用嵌入模型配置）"""
        # 嵌入维度：优先使用 OpenAI 维度配置，否则使用通用维度
        embedding_dims = self.OPENAI_EMBEDDING_DIMS or self.EMBEDDING_DIMS

        vector_store_cfg: Dict[str, Any] = {
            "collection_name": self.MEM0_COLLECTION,
            "embedding_model_dims": embedding_dims,
            "url": self.MILVUS_URL,
            "metric_type": self.MILVUS_METRIC_TYPE,
            "token": self.MILVUS_TOKEN or "",
        }
        if self.MILVUS_DB_NAME is not None:
            vector_store_cfg["db_name"] = self.MILVUS_DB_NAME

        # 复用嵌入模型配置
        if self.EMBEDDING_PROVIDER.lower() == "openai":
            embedder_cfg = {
                "provider": "openai",
                "config": {
                    "model": self.OPENAI_EMBEDDING_MODEL,
                    "api_key": self.OPENAI_EMBEDDING_API_KEY,
                    "openai_base_url": self.OPENAI_EMBEDDING_BASE_URL,
                    "embedding_dims": embedding_dims,
                },
            }
        else:
            embedder_cfg = {
                "provider": "ollama",
                "config": {
                    "model": self.EMBEDDING_MODEL,
                    "embedding_dims": self.EMBEDDING_DIMS,
                    "ollama_base_url": self.OLLAMA_BASE_URL,
                },
            }

        return {
            "vector_store": {
                "provider": "milvus",
                "config": vector_store_cfg,
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": self.LLM_MODEL,
                    "api_key": self.LLM_API_KEY,
                    "openai_base_url": self.LLM_BASE_URL,
                },
            },
            "embedder": embedder_cfg,
            "custom_instructions": "请用中文提取和存储记忆事实。",
        }

    def validate_configuration(self) -> List[str]:
        """验证配置的有效性"""
        issues = []

        # 检查必需的API密钥
        if not self.LLM_API_KEY:
            issues.append("LLM_API_KEY is not set")

        # 检查 OpenAI 嵌入配置完整性
        if self.EMBEDDING_PROVIDER.lower() == "openai":
            if not self.OPENAI_EMBEDDING_API_KEY:
                issues.append("OPENAI_EMBEDDING_API_KEY is not set")
            if not self.OPENAI_EMBEDDING_BASE_URL:
                issues.append("OPENAI_EMBEDDING_BASE_URL is not set")
            if not self.OPENAI_EMBEDDING_MODEL:
                issues.append("OPENAI_EMBEDDING_MODEL is not set")

        return issues

    def get_safe_config(self) -> Dict[str, Any]:
        """获取安全的配置信息（隐藏敏感信息）"""
        config = self.model_dump()

        # 隐藏敏感信息
        sensitive_keys = [
            "LLM_API_KEY", "VISION_API_KEY",
            "OPENAI_EMBEDDING_API_KEY", "MILVUS_TOKEN",
        ]

        for key in sensitive_keys:
            if key in config and config[key]:
                config[key] = "***" + config[key][-4:] if len(config[key]) > 4 else "***"

        return config


def create_settings() -> Settings:
    """创建并验证设置"""
    settings = Settings()

    # 验证配置
    issues = settings.validate_configuration()
    if issues:
        logger.warning("Configuration issues found:")
        for issue in issues:
            logger.warning(f"  - {issue}")

    return settings


# 该代码会自动执行，并且只会执行一次（单例设计模式）
settings = create_settings()
