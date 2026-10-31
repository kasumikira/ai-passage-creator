"""文章多智能体编排器"""

import logging
from typing import TYPE_CHECKING

from app.agent.agents.content_generator import ContentGeneratorAgent
from app.agent.agents.content_merger import ContentMergerAgent
from app.agent.agents.image_analyzer import ImageAnalyzerAgent
from app.agent.agents.outline_generator import OutlineGeneratorAgent
from app.agent.agents.title_generator import TitleGeneratorAgent
from app.agent.context.stream_handler import StreamHandlerContext
from app.models.enums import SseMessageTypeEnum
from app.schemas.article import ArticleState

if TYPE_CHECKING:
    from app.services.article_agent_service import ArticleAgentService

logger = logging.getLogger(__name__)


class ArticleAgentOrchestrator:
    """多智能体编排器"""

    def __init__(self):
        self.title_agent = TitleGeneratorAgent()
        self.outline_agent = OutlineGeneratorAgent()
        self.content_agent = ContentGeneratorAgent()
        self.image_analyzer_agent = ImageAnalyzerAgent()
        self.content_merger_agent = ContentMergerAgent()

    async def execute_phase1(
        self,
        service: "ArticleAgentService",
        state: ArticleState,
        stream_handler,
    ):
        stream_context = StreamHandlerContext(stream_handler)
        logger.info("阶段1：开始生成标题方案, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent1_generate_titles",
            "标题策划",
            "started",
            "结合选题、平台受众和产品资料，整理多个标题方向。",
        )
        await self.title_agent.run(service, state, stream_context.emit)
        stream_context.emit_progress(
            "agent1_generate_titles",
            "标题策划",
            "completed",
            "标题候选已整理，结果已准备好供你选择。",
        )
        stream_context.emit(SseMessageTypeEnum.AGENT1_COMPLETE.value)
        logger.info(
            "阶段1：标题方案生成成功, taskId=%s, optionsCount=%s",
            state.task_id,
            len(state.title_options or []),
        )

    async def execute_phase2(
        self,
        service: "ArticleAgentService",
        state: ArticleState,
        stream_handler,
    ):
        stream_context = StreamHandlerContext(stream_handler)
        logger.info("阶段2：开始生成大纲, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent2_generate_outline",
            "大纲规划",
            "started",
            "根据确认后的标题、产品资料和平台规则安排内容结构。",
        )
        await self.outline_agent.run(service, state, stream_context.emit)
        stream_context.emit_progress(
            "agent2_generate_outline",
            "大纲规划",
            "completed",
            "大纲已生成，可以查看并调整。",
        )
        stream_context.emit(SseMessageTypeEnum.AGENT2_COMPLETE.value)
        logger.info("阶段2：大纲生成成功, taskId=%s", state.task_id)

    async def execute_phase3(
        self,
        service: "ArticleAgentService",
        state: ArticleState,
        stream_handler,
    ):
        stream_context = StreamHandlerContext(stream_handler)
        logger.info("阶段3：开始生成正文, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent3_generate_content",
            "正文创作",
            "started",
            "按已确认的大纲撰写正文；需要补充资料时会显示工具调用。",
        )
        await self.content_agent.run(service, state, stream_context.emit)
        stream_context.emit_progress(
            "agent3_generate_content",
            "正文创作",
            "completed",
            "正文草稿已生成。",
        )
        stream_context.emit(SseMessageTypeEnum.AGENT3_COMPLETE.value)

        logger.info("阶段3：开始分析配图需求, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent4_analyze_image_requirements",
            "配图分析",
            "started",
            "检查正文内容，确定配图位置、主题和合适的图片来源。",
        )
        await self.image_analyzer_agent.run(service, state, stream_context.emit)
        stream_context.emit_progress(
            "agent4_analyze_image_requirements",
            "配图分析",
            "completed",
            "配图需求和插入位置已整理。",
        )
        stream_context.emit(SseMessageTypeEnum.AGENT4_COMPLETE.value)

        logger.info("阶段3：开始生成配图, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent5_generate_images",
            "图片生成",
            "started",
            "按配图需求逐张生成或检索图片，并汇报每张图片的完成情况。",
        )
        await service.agent5_generate_images(state, stream_context.emit)
        stream_context.emit_progress(
            "agent5_generate_images",
            "图片生成",
            "completed",
            f"配图处理完成，共 {len(state.images or [])} 张。",
        )
        stream_context.emit(SseMessageTypeEnum.AGENT5_COMPLETE.value)

        logger.info("阶段3：开始图文合成, taskId=%s", state.task_id)
        stream_context.emit_progress(
            "agent6_merge_content",
            "图文合成",
            "started",
            "把配图插入对应正文位置，整理最终 Markdown 内容。",
        )
        self.content_merger_agent.run(service, state)
        stream_context.emit(SseMessageTypeEnum.MERGE_COMPLETE.value)
        stream_context.emit_progress(
            "agent6_merge_content",
            "图文合成",
            "completed",
            "图文稿已合成，最终结果已更新。",
        )

