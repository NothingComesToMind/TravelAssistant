"""Environment configuration shared by the API and MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = os.getenv("TRAVEL_DEMO_MODE", "true").lower() == "true"
    amap_web_key: str = os.getenv("AMAP_WEB_KEY", "")
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp")
    mcp_port: int = int(os.getenv("MCP_PORT", "8765"))
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    tool_timeout_seconds: float = float(os.getenv("TOOL_TIMEOUT_SECONDS", "12"))


settings = Settings()

