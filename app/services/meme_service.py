"""表情包检索服务"""

import base64
from io import BytesIO
import json
import logging
import httpx
from typing import Any, Optional
from urllib.parse import quote
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

from app.config import settings
from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageSearchService
from app.schemas.image import ImageData, ImageRequest

logger = logging.getLogger(__name__)

MEME_THUMBNAIL_MAX_SIZE = (512, 512)
MEME_THUMBNAIL_JPEG_QUALITY = 82


class MemeService(ImageSearchService):
    """表情包检索服务（基于 Bing 图片搜索）"""

    def __init__(self):
        self.search_url = settings.meme_search_url
        self.suffix = settings.meme_suffix
        self.timeout = settings.meme_timeout / 1000  # 转为秒
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/142.0.0.0 Safari/537.36"
                )
            }
        )

    async def search_image(self, keywords: str) -> Optional[str]:
        """兼容单图服务接口，返回候选列表中的第一张图。"""
        images = await self.search_images(keywords, limit=1)
        return images[0]["imageUrl"] if images else None

    async def search_images(self, keywords: str, limit: int = 3) -> list[dict[str, str]]:
        """搜索并下载一批表情包，失败候选跳过，成功候选生成缩略图并缓存原图 data URL。"""
        search_text = keywords + self.suffix
        logger.info("表情包搜索: %s -> %s, limit=%s", keywords, search_text, limit)

        fetch_url = self._build_search_url(search_text)
        response = await self.client.get(fetch_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        results: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for anchor in soup.select('a.iusc'):
            metadata = self._parse_metadata(anchor.get('m'))
            image_url = self._normalise_image_url(
                metadata.get("murl") or ""
            )
            if not image_url or image_url in seen_urls:
                continue
            seen_urls.add(image_url)
            try:
                image_bytes, mime_type = await self._download_image(image_url)
            except Exception:
                logger.debug(
                    "表情包原图下载失败，跳过候选: %s",
                    image_url,
                    exc_info=True,
                )
                continue
            original_data_url = self._build_data_url(image_bytes, mime_type)
            try:
                thumbnail_url = self._build_thumbnail_data_url(image_bytes)
            except Exception:
                logger.warning(
                    "表情包缩略图生成失败，回退到已下载原图: %s",
                    image_url,
                    exc_info=True,
                )
                thumbnail_url = original_data_url
            results.append({
                "imageUrl": image_url,
                "imageDataUrl": original_data_url,
                "previewUrl": thumbnail_url,
            })
            if len(results) >= limit:
                break

        logger.info("表情包检索成功: %s, count=%s", keywords, len(results))
        return results

    async def _download_image(self, image_url: str) -> tuple[bytes, str]:
        """下载原图；下载失败直接抛出，由搜索工具交给 AI 处理。"""
        response = await self.client.get(image_url)
        response.raise_for_status()
        image_bytes = response.content
        if not image_bytes:
            raise ValueError(f"表情包原图为空: {image_url}")

        mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        if not mime_type.startswith("image/"):
            raise ValueError(f"表情包原图不是图片: {image_url}")
        return image_bytes, mime_type

    @staticmethod
    def _build_data_url(image_bytes: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _build_thumbnail_data_url(image_bytes: bytes) -> str:
        """将已下载的原图缩放为供前端和多模态模型使用的 data URL。"""
        with Image.open(BytesIO(image_bytes)) as source_image:
            image = ImageOps.exif_transpose(source_image)
            image.thumbnail(MEME_THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)

            has_alpha = image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            )
            output = BytesIO()
            if has_alpha:
                image.convert("RGBA").save(output, format="PNG", optimize=True)
                mime_type = "image/png"
            else:
                image.convert("RGB").save(
                    output,
                    format="JPEG",
                    quality=MEME_THUMBNAIL_JPEG_QUALITY,
                    optimize=True,
                )
                mime_type = "image/jpeg"

        return MemeService._build_data_url(output.getvalue(), mime_type)

    async def get_image_data(self, request: ImageRequest) -> Optional[ImageData]:
        """优先使用 Agent4 已经下载的表情包 data URL，避免执行阶段再次搜索或下载。"""
        if request.resolved_url:
            return ImageData.from_url(request.resolved_url)
        return await super().get_image_data(request)

    def get_method(self) -> ImageMethodEnum:
        """获取图片服务类型"""
        return ImageMethodEnum.MEME

    def get_fallback_image(self, position: int) -> str:
        """获取降级图片"""
        return ArticleConstant.PICSUM_URL_TEMPLATE.format(position)

    def _build_search_url(self, search_text: str) -> str:
        """构建 Bing 图片搜索 URL"""
        encoded_text = quote(search_text)
        # 必须添加 mmasync=1 参数
        return f"{self.search_url}?q={encoded_text}&mmasync=1"

    def _clean_image_url(self, url: str) -> str:
        """
        清理图片 URL 参数
        移除 ?w=xxx&h=xxx 等参数，避免图片质量下降
        """
        if not url or not url.strip():
            return url

        question_mark_index = url.find("?")
        if question_mark_index > 0:
            return url[:question_mark_index]

        return url

    @staticmethod
    def _parse_metadata(raw_metadata: Optional[str]) -> dict[str, Any]:
        if not raw_metadata:
            return {}
        try:
            metadata = json.loads(raw_metadata)
        except (TypeError, json.JSONDecodeError):
            return {}
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _normalise_image_url(url: str) -> str:
        value = (url or "").strip()
        if value.startswith("//"):
            return f"https:{value}"
        return value

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
