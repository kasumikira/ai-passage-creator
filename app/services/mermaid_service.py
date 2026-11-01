"""Mermaid 流程图生成服务"""

import logging
import re
from pathlib import Path
from typing import Optional

import mermaidx

from app.config import settings
from app.constants.article import ArticleConstant
from app.models.enums import ImageMethodEnum
from app.services.image_search_service import ImageSearchService
from app.schemas.image import ImageData, ImageRequest

logger = logging.getLogger(__name__)

# mermaidx 内置的 DejaVu Sans 没有中文字形，中文会被当成缺字宽度计算，
# 导致节点框算窄、foreignObject 把中文标签裁掉。这里给度量换一个中文字体。
_CJK_FONT_FAMILY = "Mermaid CJK"
_CJK_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)
_cjk_font_ready = False


def _install_cjk_font_metrics() -> bool:
    """把 mermaidx 的文本度量字体换成系统中文字体（只影响排版宽度）。"""
    global _cjk_font_ready
    if _cjk_font_ready:
        return True

    try:
        import novasvg.fonts as nf
        from mermaidx import font_metrics
    except Exception:
        logger.warning("Mermaid 字体度量初始化失败", exc_info=True)
        return False

    for candidate in _CJK_FONT_CANDIDATES:
        font_path = Path(candidate)
        if not font_path.exists():
            continue
        try:
            nf.add_font_face_from_file(_CJK_FONT_FAMILY, False, False, str(font_path))
            nf.add_font_face_from_file(_CJK_FONT_FAMILY, True, False, str(font_path))
            # mermaidx 的度量入口不带字体参数，只能替换它内部的单例字体
            font_metrics._FAMILY = _CJK_FONT_FAMILY
            font_metrics._REGULAR = font_metrics.Font(bold=False)
            font_metrics._BOLD = font_metrics.Font(bold=True)
            _cjk_font_ready = True
            logger.info("Mermaid 文本度量已使用中文字体: %s", font_path)
            return True
        except Exception:
            logger.warning("中文字体注册失败: %s", font_path, exc_info=True)

    logger.warning("未找到可用的中文字体，Mermaid 中文标签可能显示不全")
    return False


_install_cjk_font_metrics()

# 度量字体和浏览器实际渲染字体不可能完全一致，给标签留一点余量，
# 避免最后一个字被 foreignObject 的裁剪边界切到。
_LABEL_PATTERN = re.compile(
    r'(?P<pre><g class="label"[^>]*?transform="translate\()'
    r'(?P<x>-?[\d.]+)(?P<sep>,\s*)(?P<y>-?[\d.]+)'
    r'(?P<mid>\)"[^>]*>\s*<rect\s*/>\s*<foreignObject width=")'
    r'(?P<w>[\d.]+)(?P<post>")'
)


def _add_label_padding(svg: str) -> str:
    """按比例加宽节点标签的 foreignObject，并保持水平居中。"""

    def widen(match: re.Match) -> str:
        width = float(match.group("w"))
        if width <= 0:
            return match.group(0)
        extra = max(8.0, round(width * 0.08, 2))
        x = float(match.group("x")) - extra / 2
        return "".join(
            (
                match.group("pre"),
                f"{x:.4f}".rstrip("0").rstrip("."),
                match.group("sep"),
                match.group("y"),
                match.group("mid"),
                f"{width + extra:.4f}".rstrip("0").rstrip("."),
                match.group("post"),
            )
        )

    return _LABEL_PATTERN.sub(widen, svg)


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
            image_bytes = _add_label_padding(diagram.svg()).encode("utf-8")
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
