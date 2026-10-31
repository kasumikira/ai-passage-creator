"""文章图片的数据库存储服务"""

import hashlib
import logging

import httpx
from databases import Database

from app.schemas.image import DataType, ImageData

logger = logging.getLogger(__name__)


class ArticleImageStorageService:
    """以 SHA-256 内容地址保存文章图片，并关联到文章任务和位置。"""

    def __init__(self, db: Database):
        self.db = db

    async def store(self, task_id: str, position: int, image_data: ImageData) -> str:
        if not task_id:
            raise ValueError("保存文章图片时必须提供 task_id")
        if not image_data or not image_data.is_valid():
            raise ValueError("图片数据无效")

        if image_data.data_type == DataType.URL:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_data.url)
                response.raise_for_status()
                image_bytes = response.content
                response_mime_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
                mime_type = (
                    response_mime_type
                    if response_mime_type.startswith("image/")
                    else image_data.mime_type
                )
        else:
            image_bytes = image_data.get_image_bytes()
            mime_type = image_data.mime_type

        if not image_bytes:
            raise ValueError("图片字节数据为空")

        image_hash = hashlib.sha256(image_bytes).hexdigest()
        async with self.db.transaction():
            previous_hash = await self.db.fetch_val(
                query="""
                    SELECT imageSha256 FROM article_image
                    WHERE taskId = :taskId AND position = :position
                """,
                values={"taskId": task_id, "position": position},
            )
            await self.db.execute(
                query="""
                    INSERT INTO image_blob (sha256, mimeType, imageData)
                    VALUES (:sha256, :mimeType, :imageData)
                    ON DUPLICATE KEY UPDATE sha256 = VALUES(sha256)
                """,
                values={
                    "sha256": image_hash,
                    "mimeType": mime_type,
                    "imageData": image_bytes,
                },
            )
            await self.db.execute(
                query="""
                    INSERT INTO article_image (taskId, position, imageSha256)
                    VALUES (:taskId, :position, :imageSha256)
                    ON DUPLICATE KEY UPDATE imageSha256 = VALUES(imageSha256)
                """,
                values={
                    "taskId": task_id,
                    "position": position,
                    "imageSha256": image_hash,
                },
            )
            if previous_hash and previous_hash != image_hash:
                await self.db.execute(
                    query="""
                        DELETE FROM image_blob
                        WHERE sha256 = :sha256
                          AND NOT EXISTS (
                              SELECT 1 FROM article_image
                              WHERE imageSha256 = :sha256
                          )
                    """,
                    values={"sha256": previous_hash},
                )

        logger.info(
            "文章图片已存入数据库, taskId=%s, position=%s, sha256=%s, size=%s bytes",
            task_id,
            position,
            image_hash,
            len(image_bytes),
        )
        return f"dbimage://{image_hash}"
