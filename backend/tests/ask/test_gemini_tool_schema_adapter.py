import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.ask.llm import LLMPlanRequest, LLMToolSchema
from app.ask.llm.gemini_provider import GeminiProvider
from app.ask.llm.gemini_schema_adapter import (
    GeminiSchemaAdapterError,
    normalize_json_schema_for_gemini,
    parse_gemini_function_call,
    to_gemini_function_declaration,
    to_gemini_tools,
    validate_llm_tool_schema,
)
from app.ask.tools_v2.registry import TOOL_CLASSES, get_llm_tool_schemas


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


class GeminiSchemaNormalizationTest(unittest.TestCase):
    def test_normalization_removes_titles_defs_and_refs(self):
        schema = {
            "title": "Tool",
            "type": "object",
            "$defs": {
                "Condition": {
                    "title": "Condition",
                    "type": "object",
                    "properties": {"metric": {"title": "Metric", "type": "string"}},
                    "required": ["metric"],
                }
            },
            "properties": {
                "condition": {"$ref": "#/$defs/Condition"},
            },
            "required": ["condition"],
        }

        normalized = normalize_json_schema_for_gemini(schema)

        self.assertNotIn("title", normalized)
        self.assertNotIn("$defs", normalized)
        self.assertEqual(normalized["properties"]["condition"]["type"], "object")
        self.assertEqual(normalized["properties"]["condition"]["required"], ["metric"])

    def test_normalization_simplifies_nullable_anyof(self):
        normalized = normalize_json_schema_for_gemini(
            {
                "type": "object",
                "properties": {
                    "year": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "description": "Optional year",
                    }
                },
            }
        )

        self.assertEqual(normalized["properties"]["year"]["type"], "integer")
        self.assertEqual(normalized["properties"]["year"]["description"], "Optional year")

    def test_normalization_preserves_enum_required_and_array_items(self):
        normalized = normalize_json_schema_for_gemini(
            {
                "type": "object",
                "properties": {
                    "order": {"type": "string", "enum": ["asc", "desc"]},
                    "metrics": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"metric": {"type": "string"}}},
                    },
                },
                "required": ["order"],
            }
        )

        self.assertEqual(normalized["properties"]["order"]["enum"], ["asc", "desc"])
        self.assertEqual(normalized["required"], ["order"])
        self.assertEqual(normalized["properties"]["metrics"]["items"]["type"], "object")


class GeminiToolConversionTest(unittest.TestCase):
    def tool_schema(self):
        return LLMToolSchema(
            name="rank_sections",
            description="Rank sections by a metric",
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "Metric key"},
                    "order": {"type": "string", "enum": ["asc", "desc"]},
                },
                "required": ["metric"],
            },
        )

    def test_converts_one_tool_to_function_declaration(self):
        declaration = to_gemini_function_declaration(self.tool_schema())

        if isinstance(declaration, dict):
            self.assertEqual(declaration["name"], "rank_sections")
            self.assertIn("metric", declaration["parameters"]["properties"])
        else:
            self.assertEqual(declaration.name, "rank_sections")
            self.assertIn("metric", declaration.parameters["properties"])

    def test_converts_multiple_tools_into_tool_list(self):
        tools = to_gemini_tools(
            [
                self.tool_schema(),
                LLMToolSchema(
                    name="aggregate_municipality",
                    description="Aggregate municipality",
                    parameters={"type": "object", "properties": {"metric": {"type": "string"}}, "required": ["metric"]},
                ),
            ]
        )

        self.assertEqual(len(tools), 1)

    def test_rejects_invalid_tool_names(self):
        with self.assertRaises(GeminiSchemaAdapterError):
            validate_llm_tool_schema(
                LLMToolSchema(name="bad-name!", description="Bad", parameters={"type": "object", "properties": {}})
            )

    def test_rejects_missing_descriptions(self):
        with self.assertRaises(GeminiSchemaAdapterError):
            validate_llm_tool_schema(
                LLMToolSchema(name="valid_name", description="", parameters={"type": "object", "properties": {}})
            )

    def test_rejects_non_object_parameters(self):
        with self.assertRaises(GeminiSchemaAdapterError):
            validate_llm_tool_schema(
                LLMToolSchema(name="valid_name", description="Bad", parameters={"type": "array", "items": {"type": "string"}})
            )


class ToolRegistryExportTest(unittest.TestCase):
    def test_get_llm_tool_schemas_returns_supported_and_beta_tools(self):
        schemas = get_llm_tool_schemas()
        names = [schema.name for schema in schemas]

        self.assertIn("rank_sections", names)
        self.assertIn("age_cohort_projection", names)
        self.assertIn("persistent_winner", names)
        self.assertIn("correlation_analysis", names)
        self.assertEqual(names, sorted(names))

    def test_get_llm_tool_schemas_can_exclude_beta(self):
        schemas = get_llm_tool_schemas(include_beta=False)
        names = [schema.name for schema in schemas]

        self.assertNotIn("cross_metric_ranking", names)
        self.assertNotIn("correlation_analysis", names)

    def test_no_duplicate_tool_names_and_all_validate(self):
        schemas = get_llm_tool_schemas()
        names = [schema.name for schema in schemas]

        self.assertEqual(len(names), len(set(names)))
        for schema in schemas:
            validate_llm_tool_schema(schema)

    def test_no_pending_tools_exported(self):
        exported_names = {schema.name for schema in get_llm_tool_schemas()}
        pending_names = {
            name
            for name, tool_class in TOOL_CLASSES.items()
            if getattr(tool_class, "status", "supported") == "pending"
        }

        self.assertTrue(exported_names.isdisjoint(pending_names))


class GeminiFunctionCallParsingTest(unittest.TestCase):
    def test_parses_mocked_function_call(self):
        call = SimpleNamespace(name="rank_sections", args={"metric": "population_total"})

        parsed = parse_gemini_function_call(call)

        self.assertEqual(parsed.tool_name, "rank_sections")
        self.assertEqual(parsed.arguments["metric"], "population_total")

    def test_handles_no_function_call_gracefully(self):
        self.assertIsNone(parse_gemini_function_call(SimpleNamespace(text="No call")))

    def test_handles_sdk_like_args_object(self):
        class ArgsObject:
            def items(self):
                return [("party", "PP")]

        call = SimpleNamespace(name="persistent_winner", args=ArgsObject())

        parsed = parse_gemini_function_call({"function_call": call})

        self.assertEqual(parsed.tool_name, "persistent_winner")
        self.assertEqual(parsed.arguments, {"party": "PP"})


class GeminiProviderSchemaIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_provider_plan_uses_gemini_schema_adapter(self):
        response = SimpleNamespace(
            function_calls=[SimpleNamespace(name="rank_sections", args={"metric": "population_total"})],
            text="",
        )
        provider = GeminiProvider(api_key="test-key", client=FakeClient(response))
        tool = LLMToolSchema(
            name="rank_sections",
            description="Rank sections",
            parameters={"type": "object", "properties": {"metric": {"type": "string"}}, "required": ["metric"]},
        )

        with patch("app.ask.llm.gemini_provider.to_gemini_tools", wraps=to_gemini_tools) as mocked_adapter:
            result = await provider.plan(LLMPlanRequest(question="Pregunta", system_prompt="", tools=[tool]))

        self.assertTrue(mocked_adapter.called)
        self.assertEqual(result.tool_call.tool_name, "rank_sections")
        self.assertEqual(result.tool_call.arguments["metric"], "population_total")

    async def test_snapshot_like_export_is_deterministic(self):
        first = [schema.model_dump() for schema in get_llm_tool_schemas()]
        second = [schema.model_dump() for schema in get_llm_tool_schemas()]
        names = [schema["name"] for schema in first]

        self.assertGreater(len(first), 0)
        self.assertIn("rank_sections", names)
        self.assertIn("age_cohort_projection", names)
        self.assertIn("persistent_winner", names)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
