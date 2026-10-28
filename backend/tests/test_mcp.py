import asyncio
import json

from mcp import Client

from travel_app.mcp_server import mcp


def test_mcp_tools_are_real_protocol_tools():
    async def check():
        async with Client(mcp) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert {"search_pois", "get_weather", "plan_route"} <= names
            result = await client.call_tool("search_pois", {"city": "南京", "category": "attraction"})
            assert not result.is_error
            payload = result.structured_content or json.loads(result.content[0].text)
            assert payload["pois"][0]["id"].startswith("demo-poi-")

    asyncio.run(check())

