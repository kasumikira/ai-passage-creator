"""API 路由"""

from app.routers.user import router as user_router
from app.routers.health import router as health_router
from app.routers.article import router as article_router
from app.routers.statistics import router as statistics_router
from app.routers.marketing import router as marketing_router

__all__ = [
    "user_router",
    "health_router",
    "article_router",
    "statistics_router",
    "marketing_router",
]
