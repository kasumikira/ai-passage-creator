"""Reusable, Chat Completions compatible agent runtime."""

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


ToolHandler = Callable[[dict[str, Any], "AgentContext"], Awaitable[Any]]
ToolEventHandler = Callable[[dict[str, Any]], None]


@dataclass
class AgentContext:
    """Request-scoped data shared with agents and their tools."""

    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentToolResult:
    """Tool output for the model plus optional UI-only event data."""

    content: Any
    event_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTool:
    """A function tool exposed to an agent."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class Agent:
    """An agent's instructions, tools, and optional specialist handoffs."""

    name: str
    instructions: str
    tools: list[AgentTool] = field(default_factory=list)
    handoffs: list["Agent"] = field(default_factory=list)


@dataclass
class AgentRunResult:
    final_output: str
    last_agent: str
    tool_calls: int
    handoffs: list[str]


class AgentRunner:
    """Run agents with function tools, streaming text, and peer handoffs."""

    def __init__(
        self,
        client,
        model: str,
        max_turns: int = 12,
        reasoning_effort: Optional[str] = None,
    ):
        self.client = client
        self.model = model
        self.max_turns = max_turns
        self.reasoning_effort = reasoning_effort.strip() if reasoning_effort else None

    @property
    def request_options(self) -> dict[str, str]:
        if not self.reasoning_effort:
            return {}
        return {"reasoning_effort": self.reasoning_effort}

    async def run(
        self,
        agent: Agent,
        prompt: str,
        context: Optional[AgentContext] = None,
        stream_handler: Optional[Callable[[str], None]] = None,
        reasoning_stream_handler: Optional[Callable[[str], None]] = None,
        tool_event_handler: Optional[ToolEventHandler] = None,
        first_response_handler: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> AgentRunResult:
        context = context or AgentContext()
        current_agent = agent
        messages = [
            {"role": "system", "content": current_agent.instructions},
            {"role": "user", "content": prompt},
        ]
        tool_call_count = 0
        handoffs: list[str] = []
        first_response_recorded = False

        async def record_first_response():
            nonlocal first_response_recorded
            if first_response_handler and not first_response_recorded:
                await first_response_handler()
                first_response_recorded = True

        def emit_tool_event(
            name: str,
            status: str,
            arguments: Optional[dict[str, Any]] = None,
            event_data: Optional[dict[str, Any]] = None,
        ):
            if tool_event_handler:
                event = {
                    "name": name,
                    "status": status,
                    "arguments": arguments or {},
                }
                if event_data:
                    event.update(event_data)
                tool_event_handler(event)

        for _ in range(self.max_turns):
            tools, handlers, handoff_targets = self._build_tools(current_agent)
            request: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            request.update(self.request_options)
            if tools:
                request["tools"] = tools

            if stream_handler or reasoning_stream_handler:
                request["stream"] = True
                content, reasoning_content, calls = await self._stream_turn(
                    request,
                    stream_handler,
                    reasoning_stream_handler,
                    record_first_response,
                )
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or None,
                }
                if reasoning_content:
                    assistant_message["reasoning_content"] = reasoning_content
                if calls:
                    assistant_message["tool_calls"] = calls
            else:
                response = await self.client.chat.completions.create(**request)
                message = response.choices[0].message
                content = message.content or ""
                reasoning_content = getattr(message, "reasoning_content", None) or ""
                calls = [call.model_dump() for call in (message.tool_calls or [])]
                assistant_message = {"role": "assistant", "content": message.content}
                if reasoning_content:
                    assistant_message["reasoning_content"] = reasoning_content
                if calls:
                    assistant_message["tool_calls"] = calls

            await record_first_response()

            messages.append(assistant_message)
            if not calls:
                return AgentRunResult(
                    final_output=content,
                    last_agent=current_agent.name,
                    tool_calls=tool_call_count,
                    handoffs=handoffs,
                )

            for call in calls:
                tool_call_count += 1
                function = call.get("function", {})
                name = function.get("name", "")
                call_id = call.get("id", "")

                if name in handoff_targets:
                    emit_tool_event(name, "running")
                    current_agent = handoff_targets[name]
                    handoffs.append(current_agent.name)
                    messages[0] = {
                        "role": "system",
                        "content": current_agent.instructions,
                    }
                    result = f"已将任务交接给 {current_agent.name}。"
                    emit_tool_event(name, "completed")
                else:
                    arguments = json.loads(function.get("arguments") or "{}")
                    emit_tool_event(name, "running", arguments)
                    try:
                        tool_result = await handlers[name](arguments, context)
                    except Exception as error:
                        result = f"工具调用失败：{type(error).__name__}: {error}"
                        emit_tool_event(name, "failed", arguments)
                    else:
                        event_data = {}
                        if isinstance(tool_result, AgentToolResult):
                            result = tool_result.content or ""
                            event_data = tool_result.event_data
                        else:
                            result = tool_result
                            if not isinstance(result, str):
                                result = json.dumps(result, ensure_ascii=False, default=str)
                        emit_tool_event(name, "completed", arguments, event_data)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result,
                })

        raise RuntimeError(f"Agent {agent.name} exceeded the {self.max_turns}-turn limit")

    def _build_tools(self, agent: Agent):
        tools = [tool.schema() for tool in agent.tools]
        handlers = {tool.name: tool.handler for tool in agent.tools}
        handoff_targets: dict[str, Agent] = {}

        for index, target in enumerate(agent.handoffs, start=1):
            tool_name = f"transfer_to_agent_{index}"
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"将当前任务交给 {target.name} 专家处理。",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            })
            handoff_targets[tool_name] = target

        return tools, handlers, handoff_targets

    async def _stream_turn(
        self,
        request: dict[str, Any],
        stream_handler: Optional[Callable[[str], None]],
        reasoning_stream_handler: Optional[Callable[[str], None]] = None,
        first_chunk_handler: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        stream = await self.client.chat.completions.create(**request)
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}

        first_chunk_seen = False
        async for chunk in stream:
            if first_chunk_handler and not first_chunk_seen:
                await first_chunk_handler()
                first_chunk_seen = True
            choice = chunk.choices[0]
            delta = choice.delta
            reasoning_delta = getattr(delta, "reasoning_content", None)
            if reasoning_delta:
                reasoning_parts.append(reasoning_delta)
                if reasoning_stream_handler:
                    reasoning_stream_handler(reasoning_delta)
            if delta.content:
                content_parts.append(delta.content)
                if stream_handler:
                    stream_handler(delta.content)
            for call_delta in delta.tool_calls or []:
                call = calls.setdefault(call_delta.index, {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                })
                if call_delta.id:
                    call["id"] = call_delta.id
                if call_delta.function and call_delta.function.name:
                    call["function"]["name"] += call_delta.function.name
                if call_delta.function and call_delta.function.arguments:
                    call["function"]["arguments"] += call_delta.function.arguments

        return (
            "".join(content_parts),
            "".join(reasoning_parts),
            [calls[index] for index in sorted(calls)],
        )
