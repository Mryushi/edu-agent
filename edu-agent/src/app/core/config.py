import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings

# 项目根目录（config.py 所在的 src/app/core/ 上三级）
_ROOT_DIR = Path(__file__).resolve().parents[3]
_ENV_FILE = _ROOT_DIR / ".env"

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # LLM 主模型
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str

    # 视觉模型
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str
    VISION_TEXT_MODEL: str

    # PDF 多模态
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

    # Milvus 向量库
    MILVUS_URL: str
    MILVUS_TOKEN: Optional[str] = None   # 可选，本地无鉴权时留空
    MILVUS_DB_NAME: Optional[str] = None # 可选，使用默认 db 时留空
    MILVUS_COLLECTION: str
    MILVUS_METRIC_TYPE: str

    # RAG 知识库（独立 collection）
    MILVUS_RAG_COLLECTION: str = "edu_agent_rag"
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 100
    RAG_CHUNK_MIN: int = 200
    RAG_CHUNK_MAX_LEN: int = 4000
    RAG_TOP_K: int = 5

    # RAG 混合检索：dense (qwen3-embedding) + sparse (Milvus BM25 Function)
    RAG_DENSE_EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    RAG_DENSE_EMBEDDING_DIMS: int = 1024
    RAG_HYBRID_FETCH_K: int = 20

    # mem0 LLM（提取记忆事实）
    MEMORY_LLM_MODEL: str

    # mem0 嵌入模型
    MEMORY_EMBEDDER_PROVIDER: str        # ollama / openai
    MEMORY_EMBEDDING_MODEL: str
    MEMORY_EMBEDDING_DIMS: int
    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str = "deepseek-r1:8b"

    # MCP (Model Context Protocol) 服务器配置
    MCP_SERVERS_JSON: Optional[str] = None

    # 日志
    LOG_LEVEL: str
    LOG_FILE: str
    ENABLE_DETAILED_LOGGING: bool

    class Config:
        case_sensitive = True
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"

    def get_mem0_config(self) -> Dict[str, Any]:
        """构建 mem0 Memory.from_config() 所需的配置字典。"""
        vector_store_cfg: Dict[str, Any] = {
            "collection_name": self.MILVUS_COLLECTION,
            "embedding_model_dims": self.MEMORY_EMBEDDING_DIMS,
            "url": self.MILVUS_URL,
            "metric_type": self.MILVUS_METRIC_TYPE,
            "token": self.MILVUS_TOKEN or "",
        }
        if self.MILVUS_DB_NAME is not None:
            vector_store_cfg["db_name"] = self.MILVUS_DB_NAME

        return {
            "vector_store": {
                "provider": "milvus",
                "config": vector_store_cfg,
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": self.MEMORY_LLM_MODEL,
                    "api_key": self.LLM_API_KEY,
                    "openai_base_url": self.LLM_BASE_URL,
                },
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": self.MEMORY_EMBEDDING_MODEL,
                    "embedding_dims": self.MEMORY_EMBEDDING_DIMS,
                    "ollama_base_url": self.OLLAMA_BASE_URL,
                },
            },
            "custom_instructions": "请用中文提取和存储记忆事实。",
        }


    def validate_configuration(self) -> List[str]:
        """
        验证配置的有效性

        Returns:
            配置问题列表，空列表表示配置正常
        """
        issues = []

        # 检查必需的API密钥
        if not self.LLM_API_KEY:
            issues.append("LLM_API_KEY is not set")

        return issues

    def get_safe_config(self) -> Dict[str, Any]:
        """
        获取安全的配置信息（隐藏敏感信息）

        Returns:
            安全的配置字典
        """
        config = self.model_dump()

        # 隐藏敏感信息
        sensitive_keys = ["LLM_API_KEY", "VISION_API_KEY"]

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

