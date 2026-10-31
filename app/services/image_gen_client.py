"""AI 生图客户端适配层

根据 settings.image_gen_format 选择不同的协议实现：
- google-genai: Google GenAI 协议（Gemini 系列原生生图）
- openai: OpenAI images 兼容协议（/images/generations）

各协议实现统一产出 ImageData（图片字节 + MIME 类型）。
"""

import base64
import logging

import httpx
from google import genai
from google.genai import types
from openai import AsyncOpenAI

from app.config import settings
from app.schemas.image import ImageData

logger = logging.getLogger(__name__)


class GoogleGenAiImageProvider:
    """Google GenAI 协议实现"""

    def __init__(self):
        # 端点可配置，留空使用 Google 官方地址
        client_kwargs = {"api_key": settings.image_gen_api_key}
        if settings.image_gen_base_url:
            client_kwargs["http_options"] = types.HttpOptions(
                baseUrl=settings.image_gen_base_url
            )
        self.client = genai.Client(**client_kwargs)
        self.model = settings.image_gen_model

    async def generate(self, prompt: str) -> ImageData | None:
        try:
            # Gemini 3 Pro Image 支持更高分辨率
            image_config_params = {"aspect_ratio": settings.image_gen_aspect_ratio}
            if "gemini-3-pro" in self.model:
                image_config_params["image_size"] = settings.image_gen_image_size

            config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(**image_config_params)
            )

            logger.info(
                f"Google GenAI 开始生成图片, model={self.model}, prompt={prompt}"
            )

            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )

            # 从响应中提取图片数据
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        mime_type = part.inline_data.mime_type or "image/png"

                        logger.info(
                            f"Google GenAI 图片生成成功, "
                            f"size={len(image_bytes)} bytes, mimeType={mime_type}"
                        )
                        return ImageData.from_bytes(image_bytes, mime_type)

            logger.error("Google GenAI 响应中未找到图片数据")
            return None
        except Exception as e:
            logger.error(f"Google GenAI 生成图片异常: {e}")
            return None


class OpenAiCompatImageProvider:
    """OpenAI images 兼容协议实现"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.image_gen_api_key,
            base_url=settings.image_gen_base_url or "https://api.openai.com/v1"
        )
        self.model = settings.image_gen_model

    def _map_size(self) -> str:
        """将宽高比映射为 OpenAI images 接口支持的尺寸"""
        try:
            w, h = (int(x) for x in settings.image_gen_aspect_ratio.split(":", 1))
            if w > h:
                return "1536x1024"
            if w < h:
                return "1024x1536"
            return "1024x1024"
        except ValueError:
            return "1024x1024"

    async def generate(self, prompt: str) -> ImageData | None:
        try:
            logger.info(
                f"OpenAI images 开始生成图片, model={self.model}, prompt={prompt}"
            )

            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self._map_size()
            )

            item = response.data[0] if response.data else None
            if item is None:
                logger.error("OpenAI images 响应中未找到图片数据")
                return None

            # 优先使用 base64 数据，其次下载 URL
            if item.b64_json:
                image_bytes = base64.b64decode(item.b64_json)
                logger.info(f"OpenAI images 图片生成成功, size={len(image_bytes)} bytes")
                return ImageData.from_bytes(image_bytes, "image/png")

            if item.url:
                async with httpx.AsyncClient(timeout=60.0) as http:
                    resp = await http.get(item.url)
                    resp.raise_for_status()
                mime_type = resp.headers.get("content-type", "image/png").split(";")[0]
                logger.info(f"OpenAI images 图片下载成功, size={len(resp.content)} bytes")
                return ImageData.from_bytes(resp.content, mime_type)

            logger.error("OpenAI images 响应中既无 b64_json 也无 url")
            return None
        except Exception as e:
            logger.error(f"OpenAI images 生成图片异常: {e}")
            return None


class ImageGenClient:
    """生图客户端门面，按 settings.image_gen_format 分发到对应协议实现"""

    _PROVIDERS = {
        "google-genai": GoogleGenAiImageProvider,
        "openai": OpenAiCompatImageProvider,
    }

    def __init__(self):
        fmt = (settings.image_gen_format or "").strip().lower()
        provider_cls = self._PROVIDERS.get(fmt)
        if provider_cls is None:
            raise ValueError(
                f"不支持的 IMAGE_GEN_FORMAT: {fmt!r}，可选值: {', '.join(self._PROVIDERS)}"
            )
        self.format = fmt
        self.model = settings.image_gen_model
        self._provider = provider_cls()
        logger.info("生图客户端初始化完成, format=%s, model=%s", self.format, self.model)

    async def generate(self, prompt: str) -> ImageData | None:
        """根据提示词生成图片数据，失败返回 None"""
        return await self._provider.generate(prompt)
