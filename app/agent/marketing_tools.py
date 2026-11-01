"""Reusable marketing research tools available to content and analysis agents."""

from typing import Any

from databases import Database

from app.agent.runtime import AgentContext, AgentTool, AgentToolResult
from app.config import settings


def build_marketing_tools(
    db: Database,
    enabled_image_methods: list[str] | None = None,
) -> list[AgentTool]:
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
                SELECT taskId, mainTitle, subTitle, topic, content, fullContent, createTime
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
                    "taskId": row["taskId"],
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
    tools = [
        AgentTool(
            name="search_internet",
            description="使用 Exa 搜索公开网页，返回来源链接、发布时间和相关内容摘录，用于核验营销事实。",
            parameters=query_schema,
            handler=search_internet,
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

    # 未配置限制时沿用“全部允许”的行为；配置了限制后，仅在 PEXELS 可用时暴露图片搜索工具。
    if not enabled_image_methods or "PEXELS" in enabled_image_methods:
        tools.insert(
            1,
            AgentTool(
                name="search_images",
                description="按关键词搜索可用于营销素材参考的图片，返回图片 URL。",
                parameters=query_schema,
                handler=search_images,
            ),
        )

    return tools


def build_meme_tools() -> list[AgentTool]:
    """Build the dedicated Meme search tool used by the image analyst."""

    async def search_memes(arguments: dict[str, Any], context: AgentContext):
        from app.services.meme_service import MemeService

        query = arguments["query"].strip()
        service = MemeService()
        try:
            candidates = await service.search_images(
                query,
                limit=settings.meme_default_limit,
            )
        finally:
            await service.close()

        meme_candidates = context.values.setdefault("meme_candidates", {})
        context.values.setdefault("next_meme_index", 1)
        model_content: list[dict[str, Any]] = []
        ui_items: list[dict[str, str]] = []

        for candidate in candidates:
            meme_id = f"meme_{context.values['next_meme_index']:03d}"
            context.values["next_meme_index"] += 1
            preview_url = candidate["previewUrl"]
            meme_candidates[meme_id] = {
                "memeId": meme_id,
                "imageUrl": candidate["imageUrl"],
                "imageDataUrl": candidate["imageDataUrl"],
            }
            model_content.extend([
                {"type": "text", "text": f"memeId: {meme_id}"},
                {
                    "type": "image_url",
                    "image_url": {"url": preview_url, "detail": "low"},
                },
            ])
            ui_items.append({"memeId": meme_id, "imageUrl": preview_url})

        return AgentToolResult(
            content=model_content,
            event_data={
                "result": {
                    "type": "MEME_SEARCH_RESULT",
                    "items": ui_items,
                },
            },
        )

    query_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "描述文章语境、情绪或反应的简短搜索词",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    return [
        AgentTool(
            name="search_memes",
            description="搜索一批与文章语境匹配的表情包图片；每次默认返回 3 张，并为每张图片分配 memeId。",
            parameters=query_schema,
            handler=search_memes,
        ),
    ]
