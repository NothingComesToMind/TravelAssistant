"""MCP protocol client used by specialist agents."""

import asyncio
import json
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from .config import settings


class MCPGateway:
    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        async with asyncio.timeout(settings.tool_timeout_seconds):
            # Windows system proxies can hijack localhost and turn MCP calls into HTTP 503.
            async with httpx2.AsyncClient(trust_env=False) as http_client:
                transport = streamable_http_client(settings.mcp_server_url, http_client=http_client)
                async with Client(transport) as client:
                    result = await client.call_tool(name, arguments)
        if result.is_error:
            message = " ".join(getattr(item, "text", "") for item in result.content)
            raise RuntimeError(message or f"MCP tool {name} failed")
        data = result.structured_content
        if isinstance(data, dict):
            if list(data) == ["result"] and isinstance(data["result"], dict):
                return data["result"]
            return data
        for item in result.content:
            if getattr(item, "type", None) == "text":
                parsed = json.loads(item.text)
                if isinstance(parsed, dict):
                    return parsed
        raise RuntimeError(f"MCP tool {name} returned no object")

