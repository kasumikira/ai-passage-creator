import unittest

from types import SimpleNamespace
from copy import deepcopy

from app.agent.runtime import Agent, AgentContext, AgentRunner, AgentTool
from app.agent.provenance import MaterialInput, ProvenanceRecorder


class FakeSink:
    def __init__(self):
        self.materials = []
        self.calls = []

    async def record_material(self, **kwargs):
        self.materials.append(kwargs)
        return len(self.materials)

    async def record_tool_call(self, **kwargs):
        self.calls.append(kwargs)


class ProvenanceRecorderTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_tool_archives_exact_result_and_compact_trace(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)

        async def search(arguments, context):
            return {"products": [{"id": 12, "name": "Book"}], "query": arguments["query"]}

        tool = AgentTool("search_database", "search", {}, search)
        wrapped = recorder.wrap_tools([tool])[0]
        result = await wrapped.handler({"query": "book"}, AgentContext())

        self.assertEqual(result["products"][0]["id"], 12)
        self.assertEqual(sink.materials[0]["source_type"], "tool_output")
        self.assertIn('"id": 12', sink.materials[0]["content"])
        self.assertEqual(sink.calls[0]["status"], "SUCCESS")
        self.assertEqual(sink.calls[0]["tool_name"], "search_database")
        self.assertIn("product_profile:12", sink.calls[0]["source_refs"])
        self.assertEqual(sink.calls[0]["snapshot_id"], 1)

    async def test_failed_tool_records_error_without_material(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)

        async def fail(arguments, context):
            raise ValueError("bad query")

        wrapped = recorder.wrap_tools([AgentTool("search_database", "search", {}, fail)])[0]
        with self.assertRaisesRegex(ValueError, "bad query"):
            await wrapped.handler({"query": "x"}, AgentContext())
        self.assertEqual(sink.materials, [])
        self.assertEqual(sink.calls[0]["status"], "FAILED")
        self.assertEqual(sink.calls[0]["error_message"], "bad query")

    async def test_selected_input_is_recorded_with_findable_source_ref(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)
        snapshot_id = await recorder.record_input(
            "product_profile", "product_profile:12", {"id": 12, "name": "Book"}, "Product: Book"
        )
        self.assertEqual(snapshot_id, 1)
        self.assertEqual(sink.materials[0]["source_ref"], "product_profile:12")
        self.assertEqual(sink.materials[0]["summary"], "Product: Book")

    async def test_fake_agent_run_records_inputs_after_first_response_and_tool_output(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)

        async def search(arguments, context):
            return {"products": [{"id": 12, "name": "Book"}], "historicalMaterials": []}

        class Completions:
            def __init__(self):
                self.requests = []

            async def create(self, **request):
                self.requests.append(deepcopy(request))
                if len(self.requests) == 1:
                    call = SimpleNamespace(model_dump=lambda: {
                        "id": "call-1", "function": {
                            "name": "search_database", "arguments": '{"query":"book"}'
                        }
                    })
                    message = SimpleNamespace(content=None, reasoning_content=None, tool_calls=[call])
                else:
                    message = SimpleNamespace(content="draft", reasoning_content=None, tool_calls=[])
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        completions = Completions()
        runner = AgentRunner(SimpleNamespace(chat=SimpleNamespace(completions=completions)), "fake-model")
        agent = Agent("writer", "Write from the provided facts", recorder.wrap_tools([
            AgentTool("search_database", "search", {}, search)
        ]))
        result = await recorder.run(runner, agent, "Write about Book", [
            MaterialInput("product_profile", "product_profile:12", {"id": 12, "name": "Book"}, "Product: Book")
        ])
        self.assertEqual(result.final_output, "draft")
        self.assertEqual([item["source_type"] for item in sink.materials], [
            "product_profile", "agent_instruction", "agent_prompt", "tool_output"
        ])
        self.assertIn('"id": 12', completions.requests[1]["messages"][-1]["content"])
        self.assertEqual(sink.calls[0]["status"], "SUCCESS")

    async def test_no_material_is_marked_provided_when_model_never_responds(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)

        class FailingCompletions:
            async def create(self, **request):
                raise RuntimeError("model unavailable")

        runner = AgentRunner(SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions())), "fake-model")
        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            await recorder.run(runner, Agent("writer", "instructions"), "prompt", [
                MaterialInput("product_profile", "product_profile:12", {"id": 12}, "Product")
            ])
        self.assertEqual(sink.materials, [])

    async def test_streamed_partial_response_records_inputs_before_later_failure(self):
        sink = FakeSink()
        recorder = ProvenanceRecorder("task-1", sink)

        class StreamingCompletions:
            async def create(self, **request):
                async def stream():
                    delta = SimpleNamespace(content="partial", reasoning_content=None, tool_calls=[])
                    yield SimpleNamespace(choices=[SimpleNamespace(delta=delta)])
                    raise RuntimeError("stream interrupted")
                return stream()

        runner = AgentRunner(SimpleNamespace(chat=SimpleNamespace(completions=StreamingCompletions())), "fake-model")
        with self.assertRaisesRegex(RuntimeError, "stream interrupted"):
            await recorder.run(runner, Agent("writer", "instructions"), "prompt", [
                MaterialInput("product_profile", "product_profile:12", {"id": 12}, "Product")
            ], stream_handler=lambda token: None)
        self.assertEqual([item["source_type"] for item in sink.materials], [
            "product_profile", "agent_instruction", "agent_prompt"
        ])
