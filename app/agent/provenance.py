"""Capture the material delivered to the content-writing agent."""

import hashlib
import json
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.agent.runtime import Agent, AgentRunner, AgentTool, AgentToolResult


@dataclass(frozen=True)
class MaterialInput:
    source_type: str
    source_ref: str
    content: Any
    summary: str


class ProvenanceSink(Protocol):
    async def record_material(self, **kwargs: Any) -> int: ...

    async def record_tool_call(self, **kwargs: Any) -> None: ...


def _model_content(result: Any) -> str:
    if isinstance(result, AgentToolResult):
        result = result.content or ""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, default=str)


def _source_refs(name: str, result: Any) -> list[str]:
    if isinstance(result, AgentToolResult):
        result = result.content
    refs: list[str] = []
    if name == "search_database" and isinstance(result, dict):
        refs.extend(f"product_profile:{row['id']}" for row in result.get("products", []) if row.get("id") is not None)
        refs.extend(f"article:{row['taskId']}" for row in result.get("historicalMaterials", []) if row.get("taskId"))
    elif name == "search_internet":
        refs.extend(re.findall(r"https?://[^\s<>\"']+", _model_content(result)))
    elif name == "search_images" and isinstance(result, dict) and result.get("imageUrl"):
        refs.append(result["imageUrl"])
    elif name == "get_marketing_performance":
        refs.append("mock-marketing-performance")
    return list(dict.fromkeys(refs))


def _result_summary(name: str, arguments: dict[str, Any], result: Any, length: int) -> str:
    if isinstance(result, AgentToolResult):
        result = result.content
    if name == "search_database" and isinstance(result, dict):
        return f"Found {len(result.get('products', []))} products and {len(result.get('historicalMaterials', []))} historical articles"
    if name == "search_internet":
        return f"Web search for {str(arguments.get('query', ''))[:100]} returned {length} characters"
    if name == "search_images" and isinstance(result, dict):
        return "Image search returned an image URL" if result.get("imageUrl") else "Image search returned no image"
    if name == "get_marketing_performance":
        return "Marketing performance data returned (mock data)"
    return f"{length} characters returned"


class ProvenanceRecorder:
    """Wrap content-agent tools and persist the exact output they return."""

    def __init__(self, task_id: str, sink: ProvenanceSink):
        self.task_id = task_id
        self.sink = sink

    async def record_input(self, source_type: str, source_ref: str, content: Any, summary: str) -> int:
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
        return await self.sink.record_material(
            task_id=self.task_id,
            source_type=source_type,
            source_ref=source_ref,
            content=text,
            summary=summary,
        )

    async def run(self, runner: AgentRunner, agent: Agent, prompt: str,
                  materials: Sequence[MaterialInput], **kwargs: Any):
        """Record inputs only once the model has responded to its first request."""
        async def record_delivered_inputs():
            for material in materials:
                await self.record_input(
                    material.source_type, material.source_ref,
                    material.content, material.summary,
                )
            await self.record_input(
                "agent_instruction", f"article:{self.task_id}:content-instruction",
                agent.instructions, "Content-agent system instructions",
            )
            await self.record_input(
                "agent_prompt", f"article:{self.task_id}:content-prompt",
                prompt, "Content-writing prompt and selected context",
            )

        return await runner.run(
            agent, prompt, first_response_handler=record_delivered_inputs, **kwargs
        )

    def wrap_tools(self, tools: Sequence[AgentTool]) -> list[AgentTool]:
        wrapped = []
        for tool in tools:
            async def handler(arguments: dict[str, Any], context: Any, original=tool):
                started = time.monotonic()
                try:
                    result = await original.handler(arguments, context)
                except Exception as error:
                    await self.sink.record_tool_call(
                        task_id=self.task_id,
                        tool_name=original.name,
                        arguments=arguments,
                        status="FAILED",
                        result_summary="Tool failed",
                        error_message=str(error),
                        source_refs=[],
                        snapshot_id=None,
                        duration_ms=int((time.monotonic() - started) * 1000),
                    )
                    raise
                content = _model_content(result)
                source_refs = _source_refs(original.name, result)
                summary = _result_summary(original.name, arguments, result, len(content))
                snapshot_id = await self.sink.record_material(
                    task_id=self.task_id,
                    source_type="tool_output",
                    source_ref=f"tool:{self.task_id}:{original.name}:{hashlib.sha256(json.dumps(arguments, sort_keys=True, default=str).encode()).hexdigest()[:12]}",
                    content=content,
                    summary=summary,
                )
                await self.sink.record_tool_call(
                    task_id=self.task_id,
                    tool_name=original.name,
                    arguments=arguments,
                    status="SUCCESS",
                    result_summary=summary,
                    error_message=None,
                    source_refs=source_refs,
                    snapshot_id=snapshot_id,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
                return result

            wrapped.append(AgentTool(tool.name, tool.description, tool.parameters, handler))
        return wrapped
