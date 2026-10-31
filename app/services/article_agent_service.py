"""文章智能体编排服务"""

import json
import logging
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Callable, List, Optional
from json_repair import loads as repairable_json_loads
from openai import AsyncOpenAI

from app.agent.marketing_tools import build_marketing_tools, build_meme_tools
from app.agent.runtime import Agent, AgentContext, AgentRunner
from app.agent.orchestrator import ArticleAgentOrchestrator
from app.agent.parallel.image_generator import ParallelImageGenerator
from app.config import settings
from app.constants.prompt import PromptConstant
from app.database import database
from app.managers.sse_manager import sse_emitter_manager
from app.schemas.article import (
    TitleOption,
    ArticleState,
    OutlineResult,
    OutlineSection,
    ImageRequirement,
    ImageResult,
    Agent4Result
)
from app.models.enums import SseMessageTypeEnum, ImageMethodEnum, ArticleStyleEnum
from app.services.agent_log_service import AgentLogService
from app.services.image_service_strategy import ImageServiceStrategy

logger = logging.getLogger(__name__)


class ArticleAgentService:
    """文章智能体编排服务"""

    def __init__(self):
        # 初始化 OpenAI 兼容客户端（端点与模型可配置）
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )
        self.model = settings.llm_model
        self.agent_runner = AgentRunner(
            self.client,
            self.model,
            reasoning_effort=settings.llm_reasoning_effort,
        )

        # 初始化策略模式
        self.image_service_strategy = ImageServiceStrategy(database)
        self.agent_log_service = AgentLogService(database)
        self.parallel_image_generator = ParallelImageGenerator(
            image_service_strategy=self.image_service_strategy,
            max_concurrency=settings.agent_image_max_concurrency,
        )
        self.orchestrator = ArticleAgentOrchestrator()

    async def execute_phase1_generate_titles(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """
        阶段1：生成标题方案

        Args:
            state: 文章状态
            stream_handler: 流式输出处理器
        """
        try:
            await self.orchestrator.execute_phase1(self, state, stream_handler)
        except Exception as e:
            logger.error(f"阶段1失败, taskId={state.task_id}, error={e}")
            raise RuntimeError(f"标题方案生成失败: {str(e)}")

    async def execute_phase2_generate_outline(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """阶段2：生成大纲"""
        try:
            await self.orchestrator.execute_phase2(self, state, stream_handler)
        except Exception as e:
            logger.error(f"阶段2失败, taskId={state.task_id}, error={e}")
            raise RuntimeError(f"大纲生成失败: {str(e)}")

    async def execute_phase3_generate_content(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """阶段3：生成正文、配图和合并内容"""
        try:
            await self.orchestrator.execute_phase3(self, state, stream_handler)
        except Exception as e:
            logger.error(f"阶段3失败, taskId={state.task_id}, error={e}")
            raise RuntimeError(f"正文生成失败: {str(e)}")

    async def agent1_generate_title_options(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """智能体1：生成标题方案（3-5个）"""
        prompt = PromptConstant.AGENT1_TITLE_PROMPT.replace("{topic}", state.topic)
        prompt += self._get_style_prompt(state.style)  # 风格 Prompt
        prompt = self._append_marketing_context(prompt, state)

        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent1_generate_titles",
            prompt=prompt,
            input_data={"topic": state.topic, "style": state.style},
        ) as log_data:
            content = await self._call_llm_with_streaming(prompt, stream_handler)
            title_options_data = self._parse_json_list_response(content, "标题方案")
            state.title_options = [TitleOption(**item) for item in title_options_data]
            log_data["outputData"] = self._json_dumps({"optionsCount": len(state.title_options)})
            logger.info("智能体1：标题方案生成成功, count=%s", len(state.title_options))

    async def agent2_generate_outline(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """智能体2：生成大纲（流式输出）"""
        description_section = ""
        if state.user_description and state.user_description.strip():
            description_section = PromptConstant.AGENT2_DESCRIPTION_SECTION.replace(
                "{userDescription}",
                state.user_description,
            )

        prompt = (
            PromptConstant.AGENT2_OUTLINE_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{descriptionSection}", description_section)
        )
        prompt += self._get_style_prompt(state.style)  # 风格 Prompt
        prompt = self._append_marketing_context(prompt, state)

        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent2_generate_outline",
            prompt=prompt,
            input_data={
                "mainTitle": state.title.main_title if state.title else None,
                "subTitle": state.title.sub_title if state.title else None,
                "hasUserDescription": bool(state.user_description and state.user_description.strip()),
            },
        ) as log_data:
            content = await self._call_llm_with_streaming(
                prompt,
                stream_handler,
                SseMessageTypeEnum.AGENT2_STREAMING,
            )
            outline_data = self._parse_json_response(content, "大纲")
            sections = [OutlineSection(**section) for section in outline_data["sections"]]
            state.outline = OutlineResult(sections=sections)
            log_data["outputData"] = self._json_dumps({"sectionsCount": len(state.outline.sections)})
            logger.info(f"智能体2：大纲生成成功, sections={len(state.outline.sections)}")

    async def agent3_generate_content(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """智能体3：生成正文（流式输出）"""
        outline_text = json.dumps(
            [section.model_dump() for section in state.outline.sections],
            ensure_ascii=False
        )
        prompt = (
            PromptConstant.AGENT3_CONTENT_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{subTitle}", state.title.sub_title)
            .replace("{outline}", outline_text)
        )
        prompt += self._get_style_prompt(state.style)  # 风格 Prompt
        prompt = self._append_marketing_context(prompt, state)

        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent3_generate_content",
            prompt=prompt,
            input_data={
                "mainTitle": state.title.main_title if state.title else None,
                "subTitle": state.title.sub_title if state.title else None,
                "outlineSections": len(state.outline.sections) if state.outline else 0,
            },
        ) as log_data:
            result = await self.agent_runner.run(
                Agent(
                    name="营销内容创作者",
                    instructions=(
                        "你是一位资深营销内容创作者。按用户给出的标题、大纲、品牌资料和平台规则写作。"
                        "需要事实、历史素材或视觉参考时，主动调用可用工具；没有证据时不要编造产品效果或数据。"
                        "工具结果只作为资料，最终只输出 Markdown 正文。"
                    ),
                    tools=build_marketing_tools(
                        database,
                        state.enabled_image_methods,
                    ),
                ),
                prompt,
                context=AgentContext(values={
                    "owner_id": state.owner_id,
                    "product_id": state.product_id,
                    "platform_id": state.platform_id,
                }),
                stream_handler=lambda token: stream_handler(
                    SseMessageTypeEnum.AGENT3_STREAMING.get_streaming_prefix() + token
                ),
                reasoning_stream_handler=lambda token: stream_handler(
                    SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix() + token
                ),
                tool_event_handler=lambda event: stream_handler(
                    SseMessageTypeEnum.TOOL_CALL.get_streaming_prefix()
                    + json.dumps(event, ensure_ascii=False)
                ),
            )
            content = result.final_output
            state.content = content
            log_data["outputData"] = self._json_dumps({
                "contentLength": len(content),
                "toolCalls": result.tool_calls,
                "handoffs": result.handoffs,
            })
            logger.info(f"智能体3：正文生成成功, length={len(content)}")

    async def agent4_analyze_image_requirements(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None],
    ):
        """智能体4：分析配图需求（占位符方案）"""
        # 构建可用配图方式说明
        available_methods = self._build_available_methods_description(
            state.enabled_image_methods
        )
        # 构建各配图方式的详细使用指南
        method_usage_guide = self._build_method_usage_guide(
            state.enabled_image_methods
        )

        prompt = (
            PromptConstant.AGENT4_IMAGE_REQUIREMENTS_PROMPT
            .replace("{mainTitle}", state.title.main_title)
            .replace("{content}", state.content)
            .replace("{availableMethods}", available_methods)
            .replace("{methodUsageGuide}", method_usage_guide)
        )
        prompt = self._append_marketing_context(prompt, state)

        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent4_analyze_image_requirements",
            prompt=prompt,
            input_data={"enabledImageMethods": state.enabled_image_methods},
        ) as log_data:
            meme_context = AgentContext(values={"meme_candidates": {}})
            agent4 = Agent(
                name="配图需求分析师",
                instructions=(
                    "你是文章配图需求分析师。严格遵守用户消息中的 JSON 输出格式。"
                    "当 imageSource 选择 MEME 时，必须先调用 search_memes，"
                    "只能使用工具返回的 memeId；不要猜测或创建 memeId。"
                    "如果工具调用失败，请根据工具错误重试或改用其他可用配图方式，"
                    "不要把错误文本写入最终 JSON。"
                ),
                tools=(
                    build_meme_tools()
                    if self._is_meme_method_available(state.enabled_image_methods)
                    else []
                ),
            )
            result = await self.agent_runner.run(
                agent4,
                prompt,
                context=meme_context,
                reasoning_stream_handler=lambda token: stream_handler(
                    SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix() + token
                ),
                tool_event_handler=lambda event: stream_handler(
                    SseMessageTypeEnum.TOOL_CALL.get_streaming_prefix()
                    + json.dumps(event, ensure_ascii=False)
                ),
            )
            content = result.final_output
            state.meme_candidates = meme_context.values.get("meme_candidates", {})
            agent4_data = self._parse_json_response(content, "配图需求")
            agent4_result = Agent4Result(**agent4_data)

            # 更新正文为包含占位符的版本
            state.content = self._normalize_placeholder_syntax(agent4_result.content_with_placeholders)

            # 删除被禁用来源对应的占位符，避免正文残留无法生成的配图标记。
            if state.enabled_image_methods:
                disallowed_placeholders = [
                    requirement.placeholder_id
                    for requirement in agent4_result.image_requirements
                    if requirement.image_source not in state.enabled_image_methods
                ]
                for placeholder_id in disallowed_placeholders:
                    for candidate in self._build_placeholder_candidates(placeholder_id):
                        state.content = state.content.replace(candidate, "")

            # 验证并过滤配图需求
            validated_requirements = self._validate_and_filter_image_requirements(
                agent4_result.image_requirements,
                state.enabled_image_methods,
                state.meme_candidates,
            )
            for requirement in validated_requirements:
                requirement.placeholder_id = self._normalize_placeholder_token(requirement.placeholder_id)

            state.image_requirements = validated_requirements
            log_data["outputData"] = self._json_dumps(
                {
                    "rawRequirementsCount": len(agent4_result.image_requirements),
                    "validatedRequirementsCount": len(validated_requirements),
                }
            )
            logger.info(
                f"智能体4：配图需求分析成功, count={len(agent4_result.image_requirements)}, "
                f"validated={len(validated_requirements)}, 已在正文中插入占位符"
            )

    async def agent5_generate_images(
        self,
        state: ArticleState,
        stream_handler: Callable[[str], None]
    ):
        """智能体5：生成配图并保存到数据库。"""
        async with self._agent_log_context(
            task_id=state.task_id,
            agent_name="agent5_generate_images",
            prompt=PromptConstant.AGENT5_IMAGE_EXECUTION_PROMPT,
            input_data={"requirementsCount": len(state.image_requirements or [])},
        ) as log_data:
            generated_pairs = await self.parallel_image_generator.generate(
                state.image_requirements or [],
                state.task_id,
                meme_candidates=state.meme_candidates,
                reasoning_stream_handler=lambda token: stream_handler(
                    SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix() + token
                ),
            )
            image_results = []

            for requirement, result in generated_pairs:
                image_source = requirement.image_source
                logger.info(
                    f"智能体5：开始获取配图, position={requirement.position}, "
                    f"imageSource={image_source}, keywords={requirement.keywords}"
                )

                image_ref = result.url
                method = result.method

                # 创建配图结果（URL 使用 SHA-256 数据库引用）
                image_result = self._build_image_result(requirement, image_ref, method)
                image_results.append(image_result)

                # 推送单张配图完成
                image_complete_message = (
                    SseMessageTypeEnum.IMAGE_COMPLETE.get_streaming_prefix() +
                    image_result.model_dump_json(by_alias=True)
                )
                stream_handler(image_complete_message)

                logger.info(
                    f"智能体5：配图已保存, position={requirement.position}, "
                    f"method={method.value}, imageRef={image_ref}"
                )

            # 并行执行后按位置排序，确保输出稳定
            state.images = sorted(image_results, key=lambda item: item.position)
            log_data["outputData"] = self._json_dumps({"imagesCount": len(image_results)})
            logger.info(f"智能体5：所有配图已生成并保存, count={len(image_results)}")

    def merge_images_into_content(self, state: ArticleState):
        """图文合成：根据占位符将配图插入正文（占位符方案）"""
        with self._agent_log_context_sync(
            task_id=state.task_id,
            agent_name="agent6_merge_content",
            prompt="merge_images_into_content",
            input_data={"imagesCount": len(state.images or [])},
        ) as log_data:
            content = state.content
            images = state.images

            if not images:
                state.full_content = content
                log_data["outputData"] = self._json_dumps({"fullContentLength": len(content or "")})
                return

            full_content = content

            # 遍历所有配图，根据占位符替换为实际图片
            for image in images:
                placeholder_candidates = self._build_placeholder_candidates(image.placeholder_id)
                if placeholder_candidates:
                    image_markdown = f"![{image.description}]({image.url})"
                    for placeholder in placeholder_candidates:
                        full_content = full_content.replace(placeholder, image_markdown)

            state.full_content = full_content
            log_data["outputData"] = self._json_dumps({"fullContentLength": len(full_content)})
            logger.info(f"图文合成完成, fullContentLength={len(full_content)}")

    # region 辅助方法

    @staticmethod
    def _append_marketing_context(prompt: str, state: ArticleState) -> str:
        if not state.marketing_context:
            return prompt
        return (
            prompt
            + "\n\n"
            + state.marketing_context
            + "\n\n请优先遵守平台规则，并以产品档案中的可验证信息为准。"
        )

    async def _call_llm(self, prompt: str, task_id: Optional[str] = None) -> str:
        """调用 LLM；关联文章任务时实时推送推理内容。"""
        if task_id:
            return await self._call_llm_with_streaming(
                prompt,
                lambda message: sse_emitter_manager.send(
                    task_id,
                    json.dumps({
                        "type": SseMessageTypeEnum.AGENT_REASONING_STREAMING.value,
                        "content": message.removeprefix(
                            SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix()
                        ),
                    }, ensure_ascii=False),
                ),
            )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **self.agent_runner.request_options,
        )
        return response.choices[0].message.content

    async def _call_llm_with_streaming(
        self,
        prompt: str,
        stream_handler: Callable[[str], None],
        message_type: Optional[SseMessageTypeEnum] = None,
    ) -> str:
        """实时推送推理；指定 message_type 时同时推送正文，始终返回完整结果。"""
        content_builder = []

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **self.agent_runner.request_options,
        )

        async for chunk in stream:
            reasoning_content = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning_content:
                stream_handler(
                    SseMessageTypeEnum.AGENT_REASONING_STREAMING.get_streaming_prefix() + reasoning_content
                )
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                content_builder.append(content)
                if message_type is not None:
                    stream_handler(message_type.get_streaming_prefix() + content)

        return "".join(content_builder)

    def _parse_json_response(self, content: str, name: str) -> dict:
        """解析 JSON 响应"""
        try:
            result = repairable_json_loads(content)
            if not isinstance(result, dict):
                raise ValueError("响应不是 JSON 对象")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"{name}解析失败, content={content}, error={e}")
            raise RuntimeError(f"{name}解析失败")
        except ValueError as e:
            logger.error(f"{name}解析失败, content={content}, error={e}")
            raise RuntimeError(f"{name}解析失败")

    def _parse_json_list_response(self, content: str, name: str) -> list:
        """解析 JSON 数组响应"""
        try:
            result = repairable_json_loads(content)
            if not isinstance(result, list):
                raise ValueError("响应不是 JSON 数组")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"{name}解析失败, content={content}, error={e}")
            raise RuntimeError(f"{name}解析失败")
        except ValueError as e:
            logger.error(f"{name}解析失败, content={content}, error={e}")
            raise RuntimeError(f"{name}解析失败")

    def _build_image_result(
        self,
        requirement: ImageRequirement,
        image_url: str,
        method: ImageMethodEnum
    ) -> ImageResult:
        """构建配图结果"""
        return ImageResult(
            position=requirement.position,
            url=image_url,
            method=method.value,
            keywords=requirement.keywords or "",
            sectionTitle=requirement.section_title,
            description=requirement.type,
            placeholderId=requirement.placeholder_id
        )

    def _get_style_prompt(self, style: Optional[str]) -> str:
        """根据风格获取对应的 Prompt 附加内容"""
        if not style:
            return ""

        try:
            style_enum = ArticleStyleEnum(style)
            style_map = {
                ArticleStyleEnum.TECH: PromptConstant.STYLE_TECH_PROMPT,
                ArticleStyleEnum.EMOTIONAL: PromptConstant.STYLE_EMOTIONAL_PROMPT,
                ArticleStyleEnum.EDUCATIONAL: PromptConstant.STYLE_EDUCATIONAL_PROMPT,
                ArticleStyleEnum.HUMOROUS: PromptConstant.STYLE_HUMOROUS_PROMPT,
            }
            return style_map.get(style_enum, "")
        except ValueError:
            return ""

    def _build_available_methods_description(
        self,
        enabled_methods: Optional[List[str]]
    ) -> str:
        """构建可用配图方式说明"""
        # 如果为空或 None，表示支持所有方式
        if not enabled_methods:
            return self._get_all_methods_description()

        # 只描述允许的方式
        descriptions = []
        for method_str in enabled_methods:
            try:
                method = ImageMethodEnum(method_str)
                if not method.is_fallback():
                    desc = self._get_method_usage_description(method)
                    descriptions.append(f"   - {method.value}: {desc}")
            except ValueError:
                continue

        return "\n".join(descriptions)

    def _get_all_methods_description(self) -> str:
        """获取所有配图方式的完整描述"""
        return """   - PEXELS: 适合真实场景、产品照片、人物照片、自然风景等写实图片
   - NANO_BANANA: 适合创意插画、信息图表、需要文字渲染、抽象概念、艺术风格等 AI 生成图片
   - MERMAID: 适合流程图、架构图、时序图、关系图、甘特图等结构化图表
   - ICONIFY: 适合图标、符号、小型装饰性图标（如：箭头、勾选、星星、心形等）
   - MEME: 适合表情包、搞笑图片、轻松幽默的配图；需要先调用表情包搜索工具
   - SVG_DIAGRAM: 适合概念示意图、思维导图样式、逻辑关系展示（不涉及精确数据）"""

    def _get_method_usage_description(self, method: ImageMethodEnum) -> str:
        """获取配图方式的使用说明"""
        descriptions = {
            ImageMethodEnum.PEXELS: "适合真实场景、产品照片、人物照片、自然风景等写实图片",
            ImageMethodEnum.NANO_BANANA: "适合创意插画、信息图表、需要文字渲染、抽象概念、艺术风格等 AI 生成图片",
            ImageMethodEnum.MERMAID: "适合流程图、架构图、时序图、关系图、甘特图等结构化图表",
            ImageMethodEnum.ICONIFY: "适合图标、符号、小型装饰性图标（如：箭头、勾选、星星、心形等）",
            ImageMethodEnum.MEME: "适合表情包、搞笑图片、轻松幽默的配图；需要先调用表情包搜索工具",
            ImageMethodEnum.SVG_DIAGRAM: "适合概念示意图、思维导图样式、逻辑关系展示（不涉及精确数据）",
        }
        return descriptions.get(method, method.value)

    def _build_method_usage_guide(
        self,
        enabled_methods: Optional[List[str]]
    ) -> str:
        """构建配图方式的详细使用指南"""
        # 如果没有限制，返回所有方式的使用指南
        methods_to_include = enabled_methods if enabled_methods else [
            "PEXELS", "NANO_BANANA", "MERMAID", "ICONIFY", "MEME", "SVG_DIAGRAM"
        ]

        guides = []
        for method_str in methods_to_include:
            guide = self._get_method_detailed_guide(method_str)
            if guide:
                guides.append(guide)

        return "\n".join(guides)

    def _get_method_detailed_guide(self, method_str: str) -> str:
        """获取单个配图方式的详细使用指南"""
        guides = {
            "PEXELS": "- PEXELS: 提供英文搜索关键词(keywords)，要准确、具体。prompt 留空。",
            "NANO_BANANA": "- NANO_BANANA: 提供详细的英文生图提示词(prompt)，描述场景、风格、细节。keywords 留空。",
            "MERMAID": "- MERMAID: 在 prompt 字段生成完整的 Mermaid 代码（如流程图、架构图）。keywords 留空。",
            "ICONIFY": "- ICONIFY: 提供英文图标关键词(keywords)，如：check、arrow、star、heart。prompt 留空。可使用 {{ICON_PLACEHOLDER_N}} 放在文字行内，也可以使用 {{IMAGE_PLACEHOLDER_N}} 独占一行。",
            "MEME": "- MEME: 必须先调用 search_memes 搜索候选图。最终只填写工具返回的 memeId，不填写 keywords 和 prompt。",
            "SVG_DIAGRAM": "- SVG_DIAGRAM: 在 prompt 字段描述示意图需求（中文），说明要表达的概念和关系。keywords 留空。\n  示例：绘制思维导图样式的图，中心是'自律'，周围4个分支：习惯、环境、反馈、系统",
        }
        return guides.get(method_str, "")

    def _validate_and_filter_image_requirements(
        self,
        requirements: List[ImageRequirement],
        enabled_methods: Optional[List[str]],
        meme_candidates: Optional[dict[str, dict[str, str]]] = None,
    ) -> List[ImageRequirement]:
        """验证并过滤配图需求"""
        validated_requirements = []

        for req in requirements:
            image_source = req.image_source

            # 验证 imageSource 是否在允许列表中
            if enabled_methods and image_source not in enabled_methods:
                logger.warning(
                    f"配图需求不符合限制被过滤, position={req.position}, "
                    f"imageSource={image_source}, enabledMethods={enabled_methods}"
                )
                continue

            if image_source == ImageMethodEnum.MEME.value:
                if not req.meme_id:
                    raise RuntimeError(f"表情包配图缺少 memeId, position={req.position}")
                if req.meme_id not in (meme_candidates or {}):
                    raise RuntimeError(
                        f"表情包配图引用了未搜索到的 memeId: {req.meme_id}"
                    )
                req.keywords = None
                req.prompt = ""
            else:
                req.meme_id = None

            validated_requirements.append(req)
            logger.debug(f"配图需求验证通过, position={req.position}, imageSource={image_source}")

        return validated_requirements

    @staticmethod
    def _is_meme_method_available(enabled_methods: Optional[List[str]]) -> bool:
        """判断当前任务是否允许 Agent4 使用 Meme 搜索工具。"""
        return not enabled_methods or ImageMethodEnum.MEME.value in enabled_methods

    async def ai_modify_outline(
        self,
        task_id: Optional[str],
        main_title: str,
        sub_title: str,
        current_outline: List[OutlineSection],
        modify_suggestion: str,
        marketing_context: Optional[str] = None,
    ) -> List[OutlineSection]:
        """AI 修改大纲"""
        current_outline_json = json.dumps(
            [item.model_dump() for item in current_outline],
            ensure_ascii=False,
        )
        prompt = (
            PromptConstant.AI_MODIFY_OUTLINE_PROMPT
            .replace("{mainTitle}", main_title)
            .replace("{subTitle}", sub_title)
            .replace("{currentOutline}", current_outline_json)
            .replace("{modifySuggestion}", modify_suggestion)
        )
        if marketing_context:
            prompt += "\n\n" + marketing_context
        async with self._agent_log_context(
            task_id=task_id or "unknown",
            agent_name="ai_modify_outline",
            prompt=prompt,
            input_data={
                "mainTitle": main_title,
                "subTitle": sub_title,
                "currentSectionsCount": len(current_outline),
            },
        ) as log_data:
            content = await self._call_llm(prompt, task_id)
            outline_data = self._parse_json_response(content, "修改后的大纲")
            sections = [OutlineSection(**section) for section in outline_data["sections"]]
            log_data["outputData"] = self._json_dumps({"sectionsCount": len(sections)})
            return sections

    @asynccontextmanager
    async def _agent_log_context(
        self,
        task_id: Optional[str],
        agent_name: str,
        prompt: Optional[str] = None,
        input_data: Optional[dict] = None,
    ):
        """异步智能体日志上下文"""
        with self._agent_log_context_sync(task_id, agent_name, prompt, input_data) as log_data:
            yield log_data

    @contextmanager
    def _agent_log_context_sync(
        self,
        task_id: Optional[str],
        agent_name: str,
        prompt: Optional[str] = None,
        input_data: Optional[dict] = None,
    ):
        """同步智能体日志上下文"""
        start_time = datetime.now()
        log_data = {
            "taskId": task_id or "unknown",
            "agentName": agent_name,
            "startTime": start_time,
            "status": "RUNNING",
            "prompt": prompt,
            "inputData": self._json_dumps(input_data),
            "outputData": None,
            "errorMessage": None,
        }
        try:
            yield log_data
            log_data["status"] = "SUCCESS"
        except Exception as exc:
            log_data["status"] = "FAILED"
            log_data["errorMessage"] = str(exc)
            raise
        finally:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            log_data["endTime"] = end_time
            log_data["durationMs"] = duration_ms
            self.agent_log_service.save_log_async(log_data)

    @staticmethod
    def _json_dumps(value: Optional[dict]) -> Optional[str]:
        """序列化日志数据；无效数据直接报错。"""
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _normalize_placeholder_token(token: Optional[str]) -> Optional[str]:
        """将占位符归一化为双层花括号格式：{{PLACEHOLDER}}"""
        if not token:
            return token
        token = token.strip()
        if token.startswith("{{{{") and token.endswith("}}}}"):
            inner = token[4:-4].strip()
            return f"{{{{{inner}}}}}"
        return token

    def _build_placeholder_candidates(self, token: Optional[str]) -> List[str]:
        """构建占位符候选（兼容双层和四层）"""
        normalized = self._normalize_placeholder_token(token)
        if not normalized:
            return []
        candidates = [normalized]
        if normalized.startswith("{{") and normalized.endswith("}}"):
            candidates.append("{{" + normalized + "}}")
        # 去重，保持顺序
        unique_candidates = []
        for item in candidates:
            if item not in unique_candidates:
                unique_candidates.append(item)
        return unique_candidates

    def _normalize_placeholder_syntax(self, content: Optional[str]) -> Optional[str]:
        """将正文中的四层占位符降级为双层，避免替换残留花括号"""
        if not content:
            return content
        for index in range(1, 50):
            image_key = f"IMAGE_PLACEHOLDER_{index}"
            icon_key = f"ICON_PLACEHOLDER_{index}"
            image_two = "{{" + image_key + "}}"
            icon_two = "{{" + icon_key + "}}"
            image_four = "{{" + image_two + "}}"
            icon_four = "{{" + icon_two + "}}"
            content = content.replace(image_four, image_two).replace(icon_four, icon_two)
        return content

    # endregion
