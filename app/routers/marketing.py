"""Marketing library and analytics APIs."""

import asyncio
import json
import logging

from databases import Database
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.agent.marketing_tools import build_marketing_tools
from app.agent.runtime import Agent, AgentRunner
from app.config import settings
from app.database import get_db
from app.deps import require_admin, require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.common import BaseResponse
from app.schemas.marketing import (
    MarketingAnalysisRequest,
    MarketingPlatformUpdateRequest,
    MarketingPlatformVO,
    ProductProfileVO,
)
from app.schemas.user import LoginUserVO
from app.services.marketing_analytics_service import get_mock_marketing_analytics
from app.services.marketing_library_service import MarketingLibraryService

router = APIRouter(prefix="/marketing", tags=["营销内容平台"])
logger = logging.getLogger(__name__)


@router.get("/platforms", response_model=BaseResponse[list[MarketingPlatformVO]])
async def list_platforms(
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_login),
):
    platforms = await MarketingLibraryService(db).list_platforms()
    return BaseResponse.success(data=platforms)


@router.put("/platforms/{platform_id}", response_model=BaseResponse[MarketingPlatformVO])
async def update_platform(
    platform_id: int,
    request: MarketingPlatformUpdateRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_admin),
):
    platform = await MarketingLibraryService(db).update_platform(
        platform_id,
        request.model_dump(by_alias=True),
    )
    return BaseResponse.success(data=platform, message="平台规则已更新")


@router.get("/products", response_model=BaseResponse[list[ProductProfileVO]])
async def list_products(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    products = await MarketingLibraryService(db).list_products(current_user.id)
    return BaseResponse.success(data=products)


@router.post("/products/import", response_class=StreamingResponse)
async def import_product(
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
) -> StreamingResponse:
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    throw_if(extension not in {"docx", "md", "ppt", "pptx", "pdf"}, ErrorCode.PARAMS_ERROR, "仅支持 .docx、.md、.ppt、.pptx 和 .pdf 文档")
    content = await file.read()
    service = MarketingLibraryService(db)

    async def event_stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def report_progress(stage: str, message: str) -> None:
            queue.put_nowait({"type": "progress", "stage": stage, "message": message})

        async def import_document():
            try:
                product = await service.import_product_document(
                    current_user.id,
                    filename,
                    content,
                    report_progress,
                )
                await queue.put({"type": "complete", "product": product})
            except Exception as exc:
                logger.exception("产品档案导入失败, filename=%s", filename)
                await queue.put({"type": "error", "message": str(exc) or "产品档案整理失败"})
            finally:
                await queue.put(None)

        task = asyncio.create_task(import_document())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/products/{product_id}", response_model=BaseResponse[bool])
async def delete_product(
    product_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    deleted = await MarketingLibraryService(db).delete_product(current_user.id, product_id)
    return BaseResponse.success(data=deleted)


@router.get("/analytics", response_model=BaseResponse[dict])
async def get_marketing_analytics(_: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=get_mock_marketing_analytics())


@router.post("/analytics/analyze", response_model=BaseResponse[dict])
async def analyze_marketing_analytics(
    request: MarketingAnalysisRequest,
    db: Database = Depends(get_db),
    _: LoginUserVO = Depends(require_login),
):
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    tools = [tool for tool in build_marketing_tools(db) if tool.name == "get_marketing_performance"]
    agent = Agent(
        name="营销效果分析师",
        instructions=(
            "你是一名营销数据分析师。根据用户提供的仪表盘数据，用中文说明主要发现、"
            "平台差异和下一步建议。数据为 mock 数据，不能描述为真实线上业绩。"
            "引用具体指标，并区分观察到的数据与推测原因。"
        ),
        tools=tools,
    )
    tool_call_details: list[dict] = []

    def collect_tool_call(event: dict) -> None:
        if event["status"] == "running":
            tool_call_details.append({
                "name": event["name"],
                "arguments": event.get("arguments", {}),
            })

    try:
        result = await AgentRunner(
            client,
            settings.llm_model,
            reasoning_effort=settings.llm_reasoning_effort,
        ).run(
            agent,
            "仪表盘数据：\n"
            + json.dumps(get_mock_marketing_analytics(), ensure_ascii=False)
            + "\n\n分析要求："
            + (request.question or "请分析本期营销效果，并给出可执行的优化建议。"),
            tool_event_handler=collect_tool_call,
        )
    finally:
        await client.close()
    return BaseResponse.success(data={
        "analysis": result.final_output,
        "toolCalls": result.tool_calls,
        "toolCallDetails": tool_call_details,
        "lastAgent": result.last_agent,
    })
