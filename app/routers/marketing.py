"""Marketing library and analytics APIs."""

import json

from databases import Database
from fastapi import APIRouter, Depends, File, UploadFile
from openai import AsyncOpenAI

from app.agent.marketing_tools import build_marketing_tools
from app.agent.runtime import Agent, AgentRunner
from app.config import settings
from app.database import get_db
from app.deps import require_admin, require_login
from app.exceptions import BusinessException, ErrorCode, throw_if
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


@router.post("/products/import", response_model=BaseResponse[ProductProfileVO])
async def import_product(
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    throw_if(extension not in {"docx", "md", "ppt", "pptx"}, ErrorCode.PARAMS_ERROR, "仅支持 .docx、.md、.ppt 和 .pptx 文档")
    try:
        content = await file.read()
        product = await MarketingLibraryService(db).import_product_document(
            current_user.id,
            filename,
            content,
        )
    except ValueError as exc:
        raise BusinessException(ErrorCode.PARAMS_ERROR, str(exc)) from exc
    return BaseResponse.success(data=product, message="产品档案已整理并保存")


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
    try:
        result = await AgentRunner(client, settings.llm_model).run(
            agent,
            "仪表盘数据：\n"
            + json.dumps(get_mock_marketing_analytics(), ensure_ascii=False)
            + "\n\n分析要求："
            + (request.question or "请分析本期营销效果，并给出可执行的优化建议。"),
        )
    finally:
        await client.close()
    return BaseResponse.success(data={
        "analysis": result.final_output,
        "toolCalls": result.tool_calls,
        "lastAgent": result.last_agent,
    })
