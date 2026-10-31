"""流式消息处理上下文"""

import json
from typing import Callable

from app.models.enums import SseMessageTypeEnum


class StreamHandlerContext:
    """统一封装流式消息输出"""

    def __init__(self, stream_handler: Callable[[str], None]):
        self._stream_handler = stream_handler

    def emit(self, message: str):
        """透传 SSE 消息"""
        self._stream_handler(message)

    def emit_progress(self, agent: str, title: str, status: str, summary: str):
        """发送面向用户的简短 Agent 进度摘要。"""
        payload = json.dumps(
            {
                "agent": agent,
                "title": title,
                "status": status,
                "summary": summary,
            },
            ensure_ascii=False,
        )
        self.emit(SseMessageTypeEnum.AGENT_PROGRESS.get_streaming_prefix() + payload)

