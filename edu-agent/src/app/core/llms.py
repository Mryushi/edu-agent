import logging
from langchain_core.language_models import ModelProfile
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_image_model():
    """创建图片处理模型（视觉模型）"""
    try:
        return ChatOpenAI(
            base_url=settings.VISION_BASE_URL,
            api_key=settings.VISION_API_KEY,
            model=settings.VISION_MODEL,
        )
    except Exception as e:
        logger.error(f"Failed to create image model: {e}")
        return None


def create_text_model():
    """创建主文本模型"""
    try:
        model = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=0.3,
        )
        model.profile = ModelProfile(max_input_tokens=120000)
        return model
    except Exception as e:
        logger.error(f"Failed to create text model: {e}")
        return None


def create_ollama_model():
    """创建本地 Ollama 模型"""
    try:
        from langchain_ollama import ChatOllama
        model = ChatOllama(
            model="deepseek-r1:8b",
            temperature=0.3,
        )
        model.profile = ModelProfile(max_input_tokens=120000)
        return model
    except ImportError:
        logger.warning("langchain_ollama not available")
        return None
    except Exception as e:
        logger.error(f"Failed to create ollama model: {e}")
        return None


image_llm_model = create_image_model()
text_model = create_text_model()
ollama_model = create_ollama_model()

