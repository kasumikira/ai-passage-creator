"""Reusable marketing research tools available to content and analysis agents."""

from typing import Any

from databases import Database

from app.agent.runtime import AgentContext, AgentTool


def build_marketing_tools(db: Database) -> list[AgentTool]:
    async def search_internet(arguments: dict[str, Any], _: AgentContext):
        from app.services.web_search_service import WebSearchService

        query = arguments["query"]
        results = await WebSearchService().search(query)
        return {"query": query, "results": results}

    async def search_images(arguments: dict[str, Any], _: AgentContext):
        from app.services.pexels_service import PexelsService

        service = PexelsService()
        try:
            image_url = await service.search_image(arguments["query"])
        finally:
            await service.close()
        return {"query": arguments["query"], "imageUrl": image_url}

    async def search_database(arguments: dict[str, Any], context: AgentContext):
        owner_id = context.values.get("owner_id")
        if owner_id is None:
            return {"products": [], "historicalMaterials": []}

        query = arguments["query"].strip()
        pattern = f"%{query}%"
        products = await db.fetch_all(
            query="""
                SELECT id, name, profile FROM product_profile
                WHERE ownerId = :ownerId AND isDelete = 0
                  AND (
                      id = :productId
                      OR name LIKE :pattern
                      OR profile LIKE :pattern
                  )
                ORDER BY updateTime DESC LIMIT 5
            """,
            values={
                "ownerId": owner_id,
                "productId": context.values.get("product_id") or -1,
                "pattern": pattern,
            },
        )
        materials = await db.fetch_all(
            query="""
                SELECT mainTitle, subTitle, topic, content, fullContent, createTime
                FROM article
                WHERE userId = :ownerId AND isDelete = 0 AND status = 'COMPLETED'
                  AND (
                      productId = :productId
                      OR topic LIKE :pattern
                      OR mainTitle LIKE :pattern
                      OR content LIKE :pattern
                  )
                ORDER BY createTime DESC LIMIT 5
            """,
            values={
                "ownerId": owner_id,
                "productId": context.values.get("product_id") or -1,
                "pattern": pattern,
            },
        )
        return {
            "products": [
                {"id": row["id"], "name": row["name"], "profile": row["profile"]}
                for row in products
            ],
            "historicalMaterials": [
                {
                    "title": row["mainTitle"],
                    "subtitle": row["subTitle"],
                    "topic": row["topic"],
                    "content": (row["fullContent"] or row["content"] or "")[:1800],
                    "createTime": str(row["createTime"]),
                }
                for row in materials
            ],
        }

    async def get_marketing_performance(_: dict[str, Any], __: AgentContext):
        from app.services.marketing_analytics_service import get_mock_marketing_analytics

        return get_mock_marketing_analytics()

    query_schema = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "用于搜索的简短关键词或问题"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    no_arguments_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    return [
        AgentTool(
            name="search_internet",
            description="搜索公开互联网，获取最新市场、行业和竞品信息。",
            parameters=query_schema,
            handler=search_internet,
        ),
        AgentTool(
            name="search_images",
            description="按关键词搜索可用于营销素材参考的图片，返回图片 URL。",
            parameters=query_schema,
            handler=search_images,
        ),
        AgentTool(
            name="search_database",
            description="搜索当前用户的产品档案和历史营销文章，供创作参考。",
            parameters=query_schema,
            handler=search_database,
        ),
        AgentTool(
            name="get_marketing_performance",
            description="读取营销效果仪表盘的 mock 历史数据，包含平台、趋势和高表现内容指标。",
            parameters=no_arguments_schema,
            handler=get_marketing_performance,
        ),
    ]
