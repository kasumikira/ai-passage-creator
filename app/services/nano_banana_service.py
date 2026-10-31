"""AI 生图服务（配图方式 NANO_BANANA）

实际生成逻辑由 image_gen_client 适配层完成，
协议格式通过 IMAGE_GEN_FORMAT 切换（google-genai / openai）。
"""

import logging
from typing import Optional

from app.config import settings
from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image_gen_client import ImageGenClient
from app.services.image_search_service import ImageSearchService
from app.schemas.image import ImageData, ImageRequest

logger = logging.getLogger(__name__)


class NanoBananaService(ImageSearchService):
    """AI 生图服务（配图方式 NANO_BANANA）"""

    def __init__(self):
        self.image_gen = ImageGenClient()

    async def search_image(self, keywords: str) -> Optional[str]:
        """此方法已废弃，请使用 get_image_data()"""
        return None

    async def get_image_data(self, request: ImageRequest) -> Optional[ImageData]:
        """获取图片数据"""
        prompt = request.get_effective_param(True)
        return await self.generate_image_data(prompt)

    async def generate_image_data(self, prompt: str) -> Optional[ImageData]:
        """
        根据提示词生成图片数据

        Args:
            prompt: 生图提示词

        Returns:
            ImageData 包含图片字节数据，生成失败返回 None
        """
        return await self.image_gen.generate(prompt)

    def get_method(self) -> ImageMethodEnum:
        """获取配图方式"""
        return ImageMethodEnum.NANO_BANANA

    def get_fallback_image(self, position: int) -> str:
        """获取降级图片"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position)
