"""Exa web search used by marketing agents."""

from mcp import Client
from mcp.types import TextContent

EXA_MCP_URL = "https://mcp.exa.ai/mcp"
EXA_SEARCH_TOOL = "web_search_exa"


class WebSearchService:
    async def search(self, query: str) -> str:
        async with Client(EXA_MCP_URL) as client:
            result = await client.call_tool(
                EXA_SEARCH_TOOL,
                {"query": query, "numResults": 5},
            )

        content = "\n\n".join(
            block.text for block in result.content if isinstance(block, TextContent)
        )
        if result.is_error:
            raise RuntimeError(content or "Exa MCP 搜索失败")
        return content
