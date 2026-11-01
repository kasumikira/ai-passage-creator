"""Owner-scoped read access to content-agent provenance."""

from databases import Database
from fastapi import APIRouter, Depends

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if_not
from app.schemas.common import BaseResponse
from app.schemas.user import LoginUserVO
from app.services.provenance_service import ProvenanceService
from app.services.article_service import ArticleService

router = APIRouter(prefix="/article", tags=["文章依据"])


@router.get("/{task_id}/trace", response_model=BaseResponse[list[dict]])
async def get_article_trace(
    task_id: str,
    db: Database = Depends(get_db),
    user: LoginUserVO = Depends(require_login),
):
    await ArticleService(db).require_article_access(task_id, user)
    return BaseResponse.success(data=await ProvenanceService(db).get_trace(task_id))


@router.get("/{task_id}/materials/{snapshot_id}", response_model=BaseResponse[dict])
async def get_article_material(
    task_id: str,
    snapshot_id: int,
    db: Database = Depends(get_db),
    user: LoginUserVO = Depends(require_login),
):
    await ArticleService(db).require_article_access(task_id, user)
    material = await ProvenanceService(db).get_material(task_id, snapshot_id)
    throw_if_not(material, ErrorCode.NOT_FOUND_ERROR, "资料版本不存在")
    return BaseResponse.success(data=material)
