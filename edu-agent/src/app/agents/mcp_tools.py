"""
MCP (Model Context Protocol) 工具集成

通过 MultiServerMCPClient 连接多个 MCP 服务器，动态获取工具。
配置统一由 app.core.config.settings.MCP_SERVERS_JSON 提供。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# MCP 服务器配置
# ------------------------------------------------------------------ #
def _load_mcp_config() -> dict[str, dict[str, Any]]:
    """从 Settings 加载 MCP 服务器配置。"""
    raw = settings.MCP_SERVERS_JSON
    if not raw:
        logger.info("[MCP] 未配置 MCP 服务器（MCP_SERVERS_JSON 为空），跳过加载")
        return {}
    try:
        config = json.loads(raw)
        if isinstance(config, dict):
            logger.info("[MCP] 从配置加载 %d 个 MCP 服务器", len(config))
            return config
        logger.warning("[MCP] MCP_SERVERS_JSON 格式错误，应为字典")
    except json.JSONDecodeError as e:
        logger.warning("[MCP] MCP_SERVERS_JSON 解析失败: %s", e)
    return {}


MCP_SERVER_CONFIG: dict[str, dict[str, Any]] = _load_mcp_config()


# ------------------------------------------------------------------ #
# 工具获取
# ------------------------------------------------------------------ #
def get_mcp_tools() -> list[Any]:
    """
    连接 MCP 服务器并获取工具列表。

    如果未配置 MCP 服务器，返回空列表。
    """
    if not MCP_SERVER_CONFIG:
        return []

    try:
        client = MultiServerMCPClient(MCP_SERVER_CONFIG)
        tools = asyncio.run(client.get_tools())
        logger.info("[MCP] 已加载 %d 个 MCP 工具", len(tools))
        for t in tools:
            logger.info("[MCP]   - %s", getattr(t, "name", str(t)))
        return tools
    except Exception as e:
        logger.error("[MCP] 获取 MCP 工具失败: %s", e)
        return []


# ------------------------------------------------------------------ #
# 懒加载单例
# ------------------------------------------------------------------ #
_mcp_tools: list[Any] | None = None


def get_mcp_tools_cached() -> list[Any]:
    """获取缓存的 MCP 工具列表（避免重复连接服务器）。"""
    global _mcp_tools
    if _mcp_tools is None:
        _mcp_tools = get_mcp_tools()
    return _mcp_tools
