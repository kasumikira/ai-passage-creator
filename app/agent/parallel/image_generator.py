"""并行配图生成执行器"""

import asyncio
import logging
from typing import Callable, List, Optional, Tuple

from app.models.enums import ImageMethodEnum
from app.schemas.article import ImageRequirement
from app.schemas.image import ImageRequest


logger = logging.getLogger(__name__)


class ParallelImageGenerator:
    """并行配图生成器"""

    def __init__(self, image_service_strategy, max_concurrency: int):
        self.image_service_strategy = image_service_strategy
        self.max_concurrency = max(1, max_concurrency)

    async def generate(
        self,
        requirements: List[ImageRequirement],
        task_id: str,
        meme_candidates: Optional[dict[str, dict[str, str]]] = None,
        reasoning_stream_handler: Optional[Callable[[str], None]] = None,
    ) -> List[Tuple[ImageRequirement, object]]:
        """并行生成图片，按输入顺序返回结果"""
        if not requirements:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _generate_single(requirement: ImageRequirement):
            async with semaphore:
                resolved_url = None
                if requirement.image_source == ImageMethodEnum.MEME.value:
                    candidate = (meme_candidates or {}).get(requirement.meme_id or "")
                    if not candidate:
                        raise RuntimeError(
                            f"表情包候选不存在: {requirement.meme_id or '<empty>'}"
                        )
                    resolved_url = candidate["imageDataUrl"]

                image_request = ImageRequest(
                    keywords=requirement.keywords,
                    prompt=requirement.prompt,
                    position=requirement.position,
                    type=requirement.type,
                    resolved_url=resolved_url,
                )
                result = await self.image_service_strategy.get_image_and_store(
                    task_id,
                    requirement.image_source,
                    image_request,
                    reasoning_stream_handler=reasoning_stream_handler,
                )
                return requirement, result

        tasks = [asyncio.create_task(_generate_single(req)) for req in requirements]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            # 整体任务取消时，等待所有配图任务清理；单图失败不影响其他任务。
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        generated_pairs: List[Tuple[ImageRequirement, object]] = []
        first_error = None
        for requirement, item in zip(requirements, results):
            if isinstance(item, BaseException):
                if not isinstance(item, Exception):
                    raise item
                logger.error(
                    "配图生成失败, taskId=%s, position=%s",
                    task_id, requirement.position,
                    exc_info=(type(item), item, item.__traceback__),
                )
                if first_error is None:
                    first_error = item
                continue
            generated_pairs.append(item)

        if first_error and not generated_pairs:
            raise first_error
        return generated_pairs
