"""Mermaid 流程图生成服务"""

import logging
from typing import Optional

import mermaidx

from app.config import settings
from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageSearchService
from app.schemas.image import ImageData, ImageRequest

logger = logging.getLogger(__name__)


class MermaidService(ImageSearchService):
    """Mermaid 流程图生成服务"""

    def __init__(self):
        self.background_color = settings.mermaid_background_color
        self.output_format = settings.mermaid_output_format
        self.width = settings.mermaid_width

    async def search_image(self, keywords: str) -> Optional[str]:
        """此方法已废弃，请使用 get_image_data()"""
        return None

    async def get_image(self, request: ImageRequest) -> Optional[str]:
        """此方法已废弃，请使用 get_image_data()"""
        return None

    async def get_image_data(self, request: ImageRequest) -> Optional[ImageData]:
        """获取图片数据"""
        # 优先使用 prompt（Mermaid 代码），否则使用 keywords
        mermaid_code = request.get_effective_param(True)
        return await self.generate_diagram_data(mermaid_code)

    async def generate_diagram_data(self, mermaid_code: str) -> Optional[ImageData]:
        """
        生成 Mermaid 图表数据

        Args:
            mermaid_code: Mermaid 代码

        Returns:
            图片字节数据，生成失败返回 None
        """
        if not mermaid_code or not mermaid_code.strip():
            logger.warning("Mermaid 代码为空")
            return None

        diagram = mermaidx.render(mermaid_code)
        output_format = self.output_format.lower()
        if output_format == "svg":
            image_bytes = diagram.svg().encode("utf-8")
        elif output_format == "png":
            image_bytes = diagram.png(
                width=self.width,
                background=self.background_color,
            )
        elif output_format == "pdf":
            image_bytes = diagram.pdf(
                width=self.width,
                background=self.background_color,
            )
        else:
            raise ValueError(f"不支持的 Mermaid 输出格式: {self.output_format}")

        # 确定 MIME 类型
        mime_type = self._get_mime_type()

        logger.info(
            f"Mermaid 图表生成成功, size={len(image_bytes)} bytes, "
            f"format={self.output_format}"
        )

        return ImageData.from_bytes(image_bytes, mime_type)

    def _get_mime_type(self) -> str:
        """根据输出格式获取 MIME 类型"""
        format_lower = self.output_format.lower()
        if format_lower == "png":
            return "image/png"
        elif format_lower == "svg":
            return "image/svg+xml"
        elif format_lower == "pdf":
            return "application/pdf"
        else:
            return "image/png"

    def get_method(self) -> ImageMethodEnum:
        """获取图片服务类型"""
        return ImageMethodEnum.MERMAID

    def get_fallback_image(self, position: int) -> str:
        """获取降级图片"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position)
