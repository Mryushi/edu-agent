import logging
from langchain_core.language_models import ModelProfile
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_image_model():
    """创建图片处理模型（视觉模型）

    Raises:
        RuntimeError: 模型创建失败时抛出异常，确保启动时 fail-fast
    """
    try:
        return ChatOpenAI(
            base_url=settings.VISION_BASE_URL,
            api_key=settings.VISION_API_KEY,
            model=settings.VISION_MODEL,
            timeout=120,       # 单次请求超时 120s（图片处理较慢）
            max_retries=2,     # 失败自动重试 2 次
        )
    except Exception as e:
        logger.error(f"Failed to create image model: {e}")
        raise RuntimeError(f"Failed to create image model: {e}") from e


def create_text_model():
    """创建主文本模型

    Raises:
        RuntimeError: 模型创建失败时抛出异常，确保启动时 fail-fast
    """
    try:
        model = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=0.3,
            timeout=90,        # 单次请求超时 90s
            max_retries=2,     # 失败自动重试 2 次
        )
        model.profile = ModelProfile(max_input_tokens=120000)
        return model
    except Exception as e:
        logger.error(f"Failed to create text model: {e}")
        raise RuntimeError(f"Failed to create text model: {e}") from e


def create_rag_dense_embedder():
    """创建 RAG 稠密向量嵌入模型

    根据 EMBEDDING_PROVIDER 配置选择嵌入模型提供商：
    - ollama：使用本地 Ollama 嵌入模型（默认）
    - openai：使用 OpenAI 兼容接口的嵌入模型

    Raises:
        RuntimeError: 模型创建失败时抛出异常，确保启动时 fail-fast
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        return _create_openai_embedding()
    else:
        return _create_ollama_embedding()


def _create_ollama_embedding():
    """创建 Ollama 嵌入模型"""
    model = settings.EMBEDDING_MODEL
    base_url = settings.OLLAMA_BASE_URL
    dimensions = settings.embedding_dimensions

    try:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=model,
            base_url=base_url,
            dimensions=dimensions,
        )
    except ImportError:
        logger.error("langchain_ollama not available, RAG embeddings will not work")
        raise RuntimeError("langchain_ollama is required for RAG embeddings. Install it with: pip install langchain-ollama")
    except Exception as e:
        logger.error(f"Failed to create Ollama embedding model: {e}")
        raise RuntimeError(f"Failed to create Ollama embedding model: {e}") from e


def _create_openai_embedding():
    """创建 OpenAI 兼容接口的嵌入模型

    支持任何 OpenAI 兼容的嵌入服务，如：
    - OpenAI 官方 API
    - Azure OpenAI
    - 本地 vLLM / Ollama OpenAI 兼容接口
    - 其他第三方 OpenAI 兼容服务
    """
    api_key = settings.OPENAI_EMBEDDING_API_KEY
    base_url = settings.OPENAI_EMBEDDING_BASE_URL
    model = settings.OPENAI_EMBEDDING_MODEL

    if not api_key or not base_url or not model:
        raise RuntimeError(
            "OpenAI embedding provider requires: OPENAI_EMBEDDING_API_KEY, "
            "OPENAI_EMBEDDING_BASE_URL, OPENAI_EMBEDDING_MODEL"
        )

    # 根据 EMBEDDING_PROVIDER 选择对应维度配置
    dimensions = settings.embedding_dimensions

    try:
        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            dimensions=dimensions,
            check_embedding_ctx_length=False,  # 非 OpenAI 供应商直接发送原始文本，绕过 tiktoken
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI embedding model: {e}")
        raise RuntimeError(f"Failed to create OpenAI embedding model: {e}") from e


image_llm_model = create_image_model()
text_model = create_text_model()
rag_dense_embedder = create_rag_dense_embedder()

