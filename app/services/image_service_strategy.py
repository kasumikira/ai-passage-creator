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
from app.services.emoji_pack_service import EmojiPackService
from app.services.svg_diagram_service import SvgDiagramService
from app.services.article_image_storage_service import ArticleImageStorageService
from app.schemas.image import ImageRequest, ImageData
from app.constants.article import ArticleConstant

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
            ImageMethodEnum.EMOJI_PACK: EmojiPackService,
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
        request: ImageRequest
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
            logger.warning(f"图片服务不可用: {method}, 尝试降级")
            return await self._handle_fallback_and_store(task_id, request.position)

        try:
            # 1. 获取图片数据
            image_data = await service.get_image_data(request)

            if image_data is None or not image_data.is_valid():
                logger.warning(f"图片数据获取失败, 使用降级方案, method={method}")
                return await self._handle_fallback_and_store(task_id, request.position)

            image_ref = await self.image_storage_service.store(
                task_id,
                request.position or 1,
                image_data,
            )
            logger.info("图片获取并存储成功, method=%s, imageRef=%s", method, image_ref)
            return ImageResult(image_ref, method)
        except Exception as e:
            logger.error(f"获取图片并存储异常, method={method}, error={e}")
            return await self._handle_fallback_and_store(task_id, request.position)

    def _resolve_method(self, image_source: str) -> ImageMethodEnum:
        """解析图片来源，处理未知值"""
        try:
            return ImageMethodEnum(image_source)
        except ValueError:
            logger.warning(
                f"未知的图片来源: {image_source}, "
                f"默认使用 {ImageMethodEnum.get_default_search_method().value}"
            )
            return ImageMethodEnum.get_default_search_method()

    async def _handle_fallback_and_store(
        self,
        task_id: str,
        position: Optional[int],
    ) -> ImageResult:
        """使用默认图片并保存到数据库。"""
        pos = position if position else 1
        fallback_url = self._get_fallback_image(pos)
        fallback_data = ImageData.from_url(fallback_url)
        image_ref = await self.image_storage_service.store(task_id, pos, fallback_data)
        return ImageResult(image_ref, ImageMethodEnum.get_fallback_method())

    def _get_fallback_image(self, position: int) -> str:
        """获取降级图片"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position)

    def get_registered_methods(self) -> List[ImageMethodEnum]:
        """获取所有已注册的图片服务类型"""
        return list(self.service_factories.keys())
