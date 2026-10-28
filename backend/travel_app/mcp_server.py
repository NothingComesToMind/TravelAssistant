"""Our own MCP server; API details never leak into agent prompts."""

from mcp.server import MCPServer

from .config import settings
from .provider import TravelProvider


mcp = MCPServer("TravelAssistant Tools")
provider = TravelProvider()


@mcp.tool()
async def search_pois(city: str, category: str, limit: int = 15, keyword: str = "") -> dict:
    """Search attraction or hotel POIs in a city; returns IDs and coordinates."""
    return await provider.search_pois(city, category, limit, keyword)


@mcp.tool()
async def get_weather(city: str) -> dict:
    """Get available day-by-day forecast data for a city."""
    return await provider.get_weather(city)


@mcp.tool()
async def plan_route(origin: str, destination: str) -> dict:
    """Get a walking route between two longitude,latitude coordinates."""
    return await provider.plan_route(origin, destination)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=settings.mcp_port)

