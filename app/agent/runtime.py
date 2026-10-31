"""Reusable, Chat Completions compatible agent runtime."""

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


ToolHandler = Callable[[dict[str, Any], "AgentContext"], Awaitable[Any]]


@dataclass
class AgentContext:
    """Request-scoped data shared with agents and their tools."""

    values: dict[str, Any] = field(default_factory=dict)


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

    def __init__(self, client, model: str, max_turns: int = 12):
        self.client = client
        self.model = model
        self.max_turns = max_turns

    async def run(
        self,
        agent: Agent,
        prompt: str,
        context: Optional[AgentContext] = None,
        stream_handler: Optional[Callable[[str], None]] = None,
    ) -> AgentRunResult:
        context = context or AgentContext()
        current_agent = agent
        messages = [
            {"role": "system", "content": current_agent.instructions},
            {"role": "user", "content": prompt},
        ]
        tool_call_count = 0
        handoffs: list[str] = []

        for _ in range(self.max_turns):
            tools, handlers, handoff_targets = self._build_tools(current_agent)
            request: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                request["tools"] = tools

            if stream_handler:
                request["stream"] = True
                content, calls = await self._stream_turn(request, stream_handler)
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or None,
                }
                if calls:
                    assistant_message["tool_calls"] = calls
            else:
                response = await self.client.chat.completions.create(**request)
                message = response.choices[0].message
                content = message.content or ""
                calls = [call.model_dump() for call in (message.tool_calls or [])]
                assistant_message = {"role": "assistant", "content": message.content}
                if calls:
                    assistant_message["tool_calls"] = calls

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
                    current_agent = handoff_targets[name]
                    handoffs.append(current_agent.name)
                    messages[0] = {
                        "role": "system",
                        "content": current_agent.instructions,
                    }
                    result = f"已将任务交接给 {current_agent.name}。"
                else:
                    arguments = json.loads(function.get("arguments") or "{}")
                    result = await handlers[name](arguments, context)
                    if not isinstance(result, str):
                        result = json.dumps(result, ensure_ascii=False, default=str)

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

    async def _stream_turn(self, request: dict[str, Any], stream_handler: Callable[[str], None]):
        stream = await self.client.chat.completions.create(**request)
        content_parts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}

        async for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            if delta.content:
                content_parts.append(delta.content)
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

        return "".join(content_parts), [calls[index] for index in sorted(calls)]
