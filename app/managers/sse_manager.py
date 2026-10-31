"""SSE Emitter 管理器"""

import logging
import asyncio
from typing import Dict
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
SSE_HEARTBEAT_INTERVAL_SECONDS = 15
UNCONNECTED_QUEUE_TTL_SECONDS = 120


class SseEmitterManager:
    """SSE Emitter 管理器"""
    
    def __init__(self):
        # 存储所有的队列
        self._queues: Dict[str, asyncio.Queue] = {}
        self._connected: set[str] = set()
        self._cleanup_handles: Dict[str, asyncio.TimerHandle] = {}

    def prepare(self, task_id: str):
        """在任务启动前准备队列，避免 SSE 客户端连接前丢失首批事件。"""
        self._queues.setdefault(task_id, asyncio.Queue())
        self._cancel_unconnected_cleanup(task_id)
        loop = asyncio.get_running_loop()
        self._cleanup_handles[task_id] = loop.call_later(
            UNCONNECTED_QUEUE_TTL_SECONDS,
            self._discard_unconnected_queue,
            task_id,
        )
    
    def create_emitter(self, task_id: str) -> StreamingResponse:
        """
        创建 SSE Emitter
        
        Args:
            task_id: 任务ID
            
        Returns:
            StreamingResponse
        """
        # 复用任务启动时预备的队列，保留客户端连接前产生的消息。
        queue = self._queues.setdefault(task_id, asyncio.Queue())
        self._connected.add(task_id)
        self._cancel_unconnected_cleanup(task_id)
        
        logger.info(f"SSE 连接已创建, taskId={task_id}")
        
        # 创建事件流生成器
        async def event_generator():
            try:
                while True:
                    # 从队列获取消息
                    try:
                        message = await asyncio.wait_for(
                            queue.get(),
                            timeout=SSE_HEARTBEAT_INTERVAL_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
                        continue
                    
                    # 如果是完成信号，结束流
                    if message == "__COMPLETE__":
                        break
                    
                    # 格式化为 SSE 格式
                    yield f"data: {message}\n\n"
            except asyncio.CancelledError:
                logger.info(f"SSE 连接被取消, taskId={task_id}")
                raise
            except Exception:
                logger.exception("SSE 连接错误, taskId=%s", task_id)
                raise
            finally:
                # 只清理订阅队列，文章生成任务由 ArticleAsyncService 独立持有。
                if self._queues.get(task_id) is queue:
                    del self._queues[task_id]
                    self._connected.discard(task_id)
                    self._cancel_unconnected_cleanup(task_id)
                logger.info(f"SSE 连接已关闭, taskId={task_id}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    def send(self, task_id: str, message: str):
        """
        发送消息
        
        Args:
            task_id: 任务ID
            message: 消息内容
        """
        queue = self._queues.get(task_id)
        if queue is None:
            logger.debug("SSE 无订阅者，跳过推送, taskId=%s", task_id)
            return
        
        try:
            queue.put_nowait(message)
        except Exception:
            # 推送失败只影响当前订阅，不能中断文章生成和结果保存。
            logger.exception("SSE 推送失败，后台生成继续, taskId=%s", task_id)
            if self._queues.get(task_id) is queue:
                self._queues.pop(task_id, None)
                self._connected.discard(task_id)
                self._cancel_unconnected_cleanup(task_id)
            return
        logger.debug("SSE 消息发送成功, taskId=%s", task_id)
    
    def complete(self, task_id: str):
        """
        完成连接
        
        Args:
            task_id: 任务ID
        """
        self.send(task_id, "__COMPLETE__")
        logger.debug("SSE 完成信号已处理, taskId=%s", task_id)

    def exists(self, task_id: str) -> bool:
        """
        检查 Emitter 是否存在
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否存在
        """
        return task_id in self._queues

    def _discard_unconnected_queue(self, task_id: str):
        self._cleanup_handles.pop(task_id, None)
        if task_id not in self._connected:
            self._queues.pop(task_id, None)

    def _cancel_unconnected_cleanup(self, task_id: str):
        handle = self._cleanup_handles.pop(task_id, None)
        if handle:
            handle.cancel()


# 全局单例
sse_emitter_manager = SseEmitterManager()
