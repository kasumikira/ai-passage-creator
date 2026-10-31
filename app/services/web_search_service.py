"""Public web search used by marketing agents."""

import xml.etree.ElementTree as ElementTree
from urllib.parse import quote_plus

import httpx


class WebSearchService:
    async def search(self, query: str) -> list[dict[str, str]]:
        url = "https://www.bing.com/search?format=rss&q=" + quote_plus(query)
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        return [
            {
                "title": item.findtext("title", default=""),
                "url": item.findtext("link", default=""),
                "summary": item.findtext("description", default=""),
            }
            for item in root.findall("./channel/item")[:5]
        ]
