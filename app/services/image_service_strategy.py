"""图片服务策略选择器"""

import logging
from typing import Callable, Dict, List, Optional

from databases import Database

from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageSearchService
from app.services.pexels_service import PexelsService
from app.services.nano_banana_service import NanoBananaService
from app.services.mermaid_service import MermaidService
from app.services.iconify_service import IconifyService
from app.services.meme_service import MemeService
from app.services.svg_diagram_service import SvgDiagramService
from app.services.article_image_storage_service import ArticleImageStorageService
from app.schemas.image import ImageRequest

logger = logging.getLogger(__name__)


class ImageResult:
    """图片获取结果"""

    def __init__(self, url: str, method: ImageMethodEnum):
        self.url = url
        self.method = method

    def is_success(self) -> bool:
        """判断是否成功"""
        return self.url is not None and len(self.url) > 0


class ImageServiceStrategy:
    """
    图片服务策略选择器
    根据图片来源类型选择对应的图片服务实现
    """

    def __init__(self, db: Database):
        self.service_map: Dict[ImageMethodEnum, ImageSearchService] = {}
        self.service_factories: Dict[ImageMethodEnum, Callable[[], ImageSearchService]] = {
            ImageMethodEnum.PEXELS: PexelsService,
            ImageMethodEnum.NANO_BANANA: NanoBananaService,
            ImageMethodEnum.MERMAID: MermaidService,
            ImageMethodEnum.ICONIFY: IconifyService,
            ImageMethodEnum.MEME: MemeService,
            ImageMethodEnum.SVG_DIAGRAM: SvgDiagramService,
        }
        self.image_storage_service = ArticleImageStorageService(db)
        self._register_services()

    def _register_services(self):
        """注册图片服务工厂，服务客户端在实际使用时才创建。"""
        for method, factory in self.service_factories.items():
            logger.info(
                f"注册图片服务: {method.value} -> {factory.__name__} "
                f"(AI生图: {method.is_ai_generated()}, 降级: {method.is_fallback()})"
            )

    def _get_service(self, method: ImageMethodEnum) -> Optional[ImageSearchService]:
        service = self.service_map.get(method)
        if service is None:
            factory = self.service_factories.get(method)
            if factory is None:
                return None
            service = factory()
            self.service_map[method] = service
            logger.info("初始化图片服务: %s -> %s", method.value, service.__class__.__name__)
        return service

    async def get_image_and_store(
        self,
        task_id: str,
        image_source: str,
        request: ImageRequest,
        reasoning_stream_handler: Optional[Callable[[str], None]] = None,
    ) -> ImageResult:
        """
        获取图片并保存到数据库。

        Args:
            image_source: 图片来源
            request: 图片请求对象

        Returns:
            图片获取结果（包含 SHA-256 数据库引用）
        """
        method = self._resolve_method(image_source)
        service = self._get_service(method)
        if service is None or not service.is_available():
            raise RuntimeError(f"图片服务不可用: {method.value}")

        if method == ImageMethodEnum.SVG_DIAGRAM:
            image_data = await service.get_image_data(
                request, reasoning_stream_handler=reasoning_stream_handler
            )
        else:
            image_data = await service.get_image_data(request)
        if image_data is None or not image_data.is_valid():
            raise RuntimeError(f"图片数据获取失败: {method.value}")

        image_ref = await self.image_storage_service.store(
            task_id,
            request.position or 1,
            image_data,
        )
        logger.info("图片获取并存储成功, method=%s, imageRef=%s", method, image_ref)
        return ImageResult(image_ref, method)

    def _resolve_method(self, image_source: str) -> ImageMethodEnum:
        """解析来源；未知来源直接报错。"""
        return ImageMethodEnum(image_source)

    def get_registered_methods(self) -> List[ImageMethodEnum]:
        """获取所有已注册的图片服务类型"""
        return list(self.service_factories.keys())
