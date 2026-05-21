"""
Milvus 连接管理器（单例）

提供统一的 pymilvus 连接生命周期管理。
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MilvusConnectionManager:
    """Milvus 连接管理器（线程安全单例）"""

    _instance: Optional["MilvusConnectionManager"] = None
    _lock: threading.Lock = threading.Lock()
    _connected: bool = False

    def __new__(cls) -> "MilvusConnectionManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._connected = False
                    cls._instance = instance
        return cls._instance

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        """建立 Milvus 连接（幂等，线程安全）"""
        if self._connected:
            return

        with self._lock:
            if self._connected:
                return

            from pymilvus import connections

            connect_kwargs: dict[str, Any] = {"uri": settings.MILVUS_URL}
            if settings.MILVUS_TOKEN:
                connect_kwargs["token"] = settings.MILVUS_TOKEN
            if settings.MILVUS_DB_NAME:
                connect_kwargs["db_name"] = settings.MILVUS_DB_NAME

            connections.connect(**connect_kwargs)
            self._connected = True
            logger.info("[MilvusConnection] 已连接: %s", settings.MILVUS_URL)

    def ensure_connected(self) -> None:
        """确保连接已建立，未连接则自动连接"""
        if not self._connected:
            self.connect()

    def has_collection(self, name: str) -> bool:
        """检查 collection 是否存在"""
        self.ensure_connected()
        from pymilvus import utility
        return utility.has_collection(name)

    def drop_collection(self, name: str) -> None:
        """删除 collection"""
        self.ensure_connected()
        from pymilvus import utility
        if utility.has_collection(name):
            utility.drop_collection(name)
            logger.info("[MilvusConnection] 删除 collection: %s", name)
