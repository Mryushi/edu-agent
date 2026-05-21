"""
文件解析结果缓存（共享模块）

供 pdf.py、file_parser.py 等模块共用，避免缓存逻辑分散维护导致分叉。
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PARSED_DIR = Path(__file__).resolve().parent.parent / "workspace" / "parsed"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

# 大文件采样阈值（字节）
_LARGE_FILE_THRESHOLD = 10 * 1024 * 1024
# 采样块大小（字节）
_SAMPLE_SIZE = 1024 * 1024


def compute_file_hash(file_path: str | Path) -> str:
    """计算文件内容的 SHA-256 hash（大文件头尾采样，避免读取全部内容）。

    Returns:
        32 字符 hex 字符串（完整 hash，调用方可按需截断）。
    """
    path = Path(file_path)
    file_size = path.stat().st_size

    if file_size > _LARGE_FILE_THRESHOLD:
        with open(path, "rb") as f:
            head = f.read(_SAMPLE_SIZE)
            f.seek(-_SAMPLE_SIZE, 2)
            tail = f.read(_SAMPLE_SIZE)
        sample = head + tail + str(file_size).encode()
        return hashlib.sha256(sample).hexdigest()
    else:
        return hashlib.sha256(path.read_bytes()).hexdigest()


def get_cache_path(filename: str, file_hash: str) -> Path:
    """根据原始文件名和文件 hash 生成解析缓存文件路径。

    Args:
        filename: 原始文件名（仅用于路径 stem）。
        file_hash: 文件 hash（通常取 compute_file_hash 结果的前 16 位）。

    Returns:
        PARSED_DIR / {stem}_{hash_fragment}.md
    """
    stem = Path(filename).stem
    hash_fragment = file_hash[:16] if len(file_hash) > 16 else file_hash
    return PARSED_DIR / f"{stem}_{hash_fragment}.md"


def find_cache_by_hash(file_hash: str) -> Path | None:
    """按内容 hash 在 PARSED_DIR 中查找缓存文件。

    匹配文件名末尾的 hash 片段（前 16 位），不依赖文件名 stem。
    用于回退查找：同名文件上传时中间件可能加后缀导致 stem 变化。

    Args:
        file_hash: 文件内容 hash（compute_file_hash 的返回值）。

    Returns:
        匹配的缓存文件路径，未找到时返回 None。
    """
    fragment = file_hash[:16] if len(file_hash) > 16 else file_hash
    candidates = list(PARSED_DIR.glob(f"*_{fragment}.md"))
    return candidates[0] if candidates else None


def read_cache(cache_path: Path) -> str | None:
    """读取缓存文件内容。

    Returns:
        缓存文本，文件不存在或读取失败时返回 None。
    """
    try:
        return cache_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("[ParseCache] 读取缓存失败 %s: %s", cache_path, e)
        return None


def write_cache(cache_path: Path, text: str) -> bool:
    """写入缓存文件。

    Returns:
        是否写入成功。
    """
    try:
        cache_path.write_text(text, encoding="utf-8")
        logger.info("[ParseCache] 缓存已写入: %s", cache_path)
        return True
    except Exception as e:
        logger.warning("[ParseCache] 写入缓存失败 %s: %s", cache_path, e)
        return False
