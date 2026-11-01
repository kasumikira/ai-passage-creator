"""文章异步任务服务"""

import asyncio
import json
import logging
from collections.abc import Coroutine
from typing import Any, Dict, Optional

from app.schemas.article import ArticleState, OutlineSection, OutlineResult, TitleResult
from app.agent.provenance import MaterialInput
from app.models.enums import ArticlePhaseEnum, ArticleStatusEnum, SseMessageTypeEnum
from app.services.article_agent_service import ArticleAgentService
from app.services.article_service import ArticleService
from app.managers.sse_manager import sse_emitter_manager
from app.database import database
from app.services.marketing_library_service import MarketingLibraryService

logger = logging.getLogger(__name__)


class ArticleAsyncService:
    """文章异步任务服务"""

    def __init__(self):
        # 应用持有生成任务，不能让其生命周期依赖 HTTP/SSE 连接。
        self._tasks: set[asyncio.Task] = set()

    def start_task(self, coroutine: Coroutine[Any, Any, None], *, name: str):
        task = asyncio.create_task(coroutine, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task):
        self._tasks.discard(task)
        if task.cancelled():
            logger.warning("文章后台任务被取消, task=%s", task.get_name())
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "文章后台任务异常退出, task=%s", task.get_name(),
                exc_info=(type(error), error, error.__traceback__),
            )

    async def execute_phase1(
        self,
        task_id: str,
        topic: str,
        style: Optional[str] = None,
    ):
        """阶段1：异步生成标题方案"""
        logger.info("阶段1异步任务开始, taskId=%s, topic=%s, style=%s", task_id, topic, style)
        article_service = ArticleService(database)

        try:
            article_agent_service = ArticleAgentService()
            article = await article_service.get_by_task_id(task_id)
            if not article:
                raise RuntimeError("文章不存在")
            await article_service.update_article_status(task_id, ArticleStatusEnum.PROCESSING)
            await article_service.update_phase(task_id, ArticlePhaseEnum.TITLE_GENERATING)

            state = ArticleState()
            state.task_id = task_id
            state.topic = topic
            state.style = style
            await self._load_marketing_context(state, article)

            await article_agent_service.execute_phase1_generate_titles(
                state,
                lambda message: self._handle_agent_message(task_id, message, state)
            )

            await article_service.save_title_options(task_id, state.title_options or [])
            await article_service.update_phase(task_id, ArticlePhaseEnum.TITLE_SELECTING)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.TITLES_GENERATED,
                {
                    "titleOptions": [
                        item.model_dump(by_alias=True) for item in (state.title_options or [])
                    ]
                },
            )

            logger.info("阶段1异步任务完成, taskId=%s", task_id)
        except Exception as exc:
            logger.exception("阶段1异步任务失败, taskId=%s", task_id)
            await self._handle_failure(task_id, article_service, exc)

    async def execute_phase2(self, task_id: str):
        """阶段2：异步生成大纲"""
        logger.info("阶段2异步任务开始, taskId=%s", task_id)
        article_service = ArticleService(database)

        try:
            article_agent_service = ArticleAgentService()
            article = await article_service.get_by_task_id(task_id)
            if not article:
                raise RuntimeError("文章不存在")

            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"]
            await self._load_marketing_context(state, article)
            state.user_description = article["userDescription"]
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )

            await article_agent_service.execute_phase2_generate_outline(
                state,
                lambda message: self._handle_agent_message(task_id, message, state)
            )
            await article_service.save_outline(task_id, state.outline.sections if state.outline else [])
            await article_service.update_phase(task_id, ArticlePhaseEnum.OUTLINE_EDITING)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.OUTLINE_GENERATED,
                {
                    "outline": [
                        item.model_dump() for item in (state.outline.sections if state.outline else [])
                    ]
                },
            )
            logger.info("阶段2异步任务完成, taskId=%s", task_id)
        except Exception as exc:
            logger.exception("阶段2异步任务失败, taskId=%s", task_id)
            await self._handle_failure(task_id, article_service, exc)

    async def execute_phase3(self, task_id: str):
        """阶段3：异步生成正文与配图"""
        logger.info("阶段3异步任务开始, taskId=%s", task_id)
        article_service = ArticleService(database)

        try:
            article_agent_service = ArticleAgentService()
            article = await article_service.get_by_task_id(task_id)
            if not article:
                raise RuntimeError("文章不存在")

            outline_data = json.loads(article["outline"]) if article["outline"] else []
            state = ArticleState()
            state.task_id = task_id
            state.style = article["style"]
            await self._load_marketing_context(state, article)
            state.enabled_image_methods = (
                json.loads(article["enabledImageMethods"])
                if article["enabledImageMethods"]
                else None
            )
            state.title = TitleResult(
                mainTitle=article["mainTitle"],
                subTitle=article["subTitle"],
            )
            state.outline = OutlineResult(
                sections=[OutlineSection(**item) for item in outline_data]
            )

            await article_agent_service.execute_phase3_generate_content(
                state,
                lambda message: self._handle_agent_message(task_id, message, state)
            )
            await article_service.save_article_content(task_id, state)
            await article_service.update_article_status(task_id, ArticleStatusEnum.COMPLETED)

            self._send_sse_message(
                task_id,
                SseMessageTypeEnum.ALL_COMPLETE,
                {"taskId": task_id}
            )
            sse_emitter_manager.complete(task_id)
            logger.info("阶段3异步任务完成, taskId=%s", task_id)
        except Exception as exc:
            logger.exception("阶段3异步任务失败, taskId=%s", task_id)
            await self._handle_failure(task_id, article_service, exc)

    async def _handle_failure(self, task_id: str, article_service: ArticleService, error: Exception):
        """状态写入失败时，仍通知客户端并结束事件流。"""
        try:
            await article_service.update_article_status(
                task_id, ArticleStatusEnum.FAILED, str(error)
            )
        finally:
            self._send_sse_message(task_id, SseMessageTypeEnum.ERROR, {"message": str(error)})
            sse_emitter_manager.complete(task_id)

    def _handle_agent_message(self, task_id: str, message: str, state: ArticleState):
        """处理智能体消息并推送"""
        data = self._build_message_data(message, state)
        if data is not None:
            sse_emitter_manager.send(task_id, json.dumps(data, ensure_ascii=False))

    async def _load_marketing_context(self, state: ArticleState, article):
        state.owner_id = article["userId"]
        state.product_id = article["productId"]
        state.platform_id = article["platformId"]
        context = await MarketingLibraryService(database).load_creation_context(
            state.owner_id,
            state.platform_id,
            state.product_id,
        )
        state.marketing_context = context["prompt"]
        state.marketing_sources = [
            MaterialInput(
                source_type=source_type,
                source_ref=f"{source_type}:{context[key]['id']}",
                content=context[key],
                summary=f"{source_type}: {context[key]['name']}",
            )
            for key, source_type in (("platform", "marketing_platform"), ("product", "product_profile"))
            if context[key] is not None
        ]
    
    def _build_message_data(self, message: str, state: ArticleState) -> Optional[Dict[str, Any]]:
        """构建消息数据"""
        # 处理流式消息（带冒号分隔符）
        streaming_prefix2 = SseMessageTypeEnum.AGENT2_STREAMING.get_streaming_prefix()
        streaming_prefix3 = SseMessageTypeEnum.AGENT3_STREAMING.get_streaming_prefix()
        reasoning_prefix = SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix()
        image_complete_prefix = SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix()
        
        if message.startswith(streaming_prefix2):
            return self._build_streaming_data(
                SseMessageTypeEnum.AGENT2_STREAMING,
                message[len(streaming_prefix2):]
            )
        
        if message.startswith(streaming_prefix3):
            return self._build_streaming_data(
                SseMessageTypeEnum.AGENT3_STREAMING,
                message[len(streaming_prefix3):]
            )

        if message.startswith(reasoning_prefix):
            return self._build_streaming_data(
                SseMessageTypeEnum.AGENT_REASONING_STREAMING,
                message[len(reasoning_prefix):]
            )

        tool_call_prefix = SseMessageTypeEnum.TOOL_CALL.get_streaming_prefix()
        if message.startswith(tool_call_prefix):
            tool_event = json.loads(message[len(tool_call_prefix):])
            return {"type": SseMessageTypeEnum.TOOL_CALL.value, **tool_event}

        progress_prefix = SseMessageTypeEnum.AGENT_PROGRESS.get_streaming_prefix()
        if message.startswith(progress_prefix):
            progress_event = json.loads(message[len(progress_prefix):])
            return {"type": SseMessageTypeEnum.AGENT_PROGRESS.value, **progress_event}
        
        if message.startswith(image_complete_prefix):
            image_json = message[len(image_complete_prefix):]
            return self._build_image_complete_data(image_json)
        
        # 处理完成消息（枚举值）
        return self._build_complete_message_data(message, state)
    
    def _build_streaming_data(self, type_enum: SseMessageTypeEnum, content: str) -> Dict[str, Any]:
        """构建流式输出数据"""
        return {
            "type": type_enum.value,
            "content": content
        }
    
    def _build_image_complete_data(self, image_json: str) -> Dict[str, Any]:
        """构建图片完成数据"""
        return {
            "type": SseMessageTypeEnum.IMAGE_COMPLETE.value,
            "image": json.loads(image_json)
        }
    
    def _build_complete_message_data(self, message: str, state: ArticleState) -> Optional[Dict[str, Any]]:
        """构建完成消息数据"""
        data = {}
        
        if message == SseMessageTypeEnum.AGENT1_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.AGENT1_COMPLETE.value
            data["titleOptions"] = [
                item.model_dump(by_alias=True) for item in (state.title_options or [])
            ]
        elif message == SseMessageTypeEnum.AGENT2_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.AGENT2_COMPLETE.value
            data["outline"] = [s.model_dump() for s in state.outline.sections] if state.outline else []
        elif message == SseMessageTypeEnum.AGENT3_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.AGENT3_COMPLETE.value
        elif message == SseMessageTypeEnum.AGENT4_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.AGENT4_COMPLETE.value
            data["imageRequirements"] = [
                req.model_dump(by_alias=True) for req in state.image_requirements
            ] if state.image_requirements else []
        elif message == SseMessageTypeEnum.AGENT5_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.AGENT5_COMPLETE.value
            data["images"] = [
                img.model_dump(by_alias=True) for img in state.images
            ] if state.images else []
        elif message == SseMessageTypeEnum.MERGE_COMPLETE.value:
            data["type"] = SseMessageTypeEnum.MERGE_COMPLETE.value
            data["fullContent"] = state.full_content
        else:
            return None
        
        return data
    
    def _send_sse_message(
        self,
        task_id: str,
        type_enum: SseMessageTypeEnum,
        additional_data: Dict[str, Any]
    ):
        """发送 SSE 消息"""
        data = {"type": type_enum.value}
        data.update(additional_data)
        sse_emitter_manager.send(task_id, json.dumps(data, ensure_ascii=False))


# 全局单例
article_async_service = ArticleAsyncService()
