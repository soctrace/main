import os
import unittest
from types import SimpleNamespace

from app.ask.llm import LLMPlanRequest, LLMSynthesisRequest, LLMToolSchema
from app.ask.llm.errors import ProviderNotConfiguredError
from app.ask.llm.factory import get_llm_provider
from app.ask.llm.gemini_provider import GeminiProvider
from app.ask.llm.gemini_schema_adapter import sanitize_json_schema, to_gemini_function_declaration
from app.core.config import Settings, get_settings


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake Gemini response queued")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


class GeminiProviderConfigurationTest(unittest.TestCase):
    def test_provider_raises_if_api_key_missing(self):
        settings = Settings(gemini_api_key=None)

        with self.assertRaises(ProviderNotConfiguredError):
            GeminiProvider(settings=settings)

    def test_healthcheck_returns_configured_false_without_key(self):
        settings = Settings(gemini_api_key=None)
        provider = GeminiProvider(settings=settings, raise_on_missing_key=False)

        health = provider.healthcheck()

        self.assertEqual(health["provider"], "gemini")
        self.assertFalse(health["configured"])
        self.assertEqual(health["error"], "GEMINI_API_KEY is missing")

    def test_model_routing_by_complexity(self):
        settings = Settings(
            gemini_api_key="test-key",
            gemini_fast_model="fast",
            gemini_default_model="default",
            gemini_pro_model="pro",
        )
        provider = GeminiProvider(settings=settings, client=FakeClient([]))

        self.assertEqual(provider._model_for_complexity("simple"), "fast")
        self.assertEqual(provider._model_for_complexity("semi_complex"), "default")
        self.assertEqual(provider._model_for_complexity("complex"), "pro")

    def test_factory_returns_gemini_provider_when_configured(self):
        previous_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        get_settings.cache_clear()
        try:
            provider = get_llm_provider("gemini")
            self.assertIsInstance(provider, GeminiProvider)
        finally:
            if previous_key is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = previous_key
            get_settings.cache_clear()


class GeminiSchemaAdapterTest(unittest.TestCase):
    def test_tool_schema_adapter_preserves_core_schema(self):
        tool = LLMToolSchema(
            name="rank_sections",
            description="Rank sections by metric",
            parameters={
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["population_total"]},
                    "limit": {"type": "integer", "minimum": 1},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        )

        declaration = to_gemini_function_declaration(tool)

        if isinstance(declaration, dict):
            self.assertEqual(declaration["name"], "rank_sections")
            parameters = declaration["parameters"]
        else:
            self.assertEqual(declaration.name, "rank_sections")
            parameters = declaration.parameters
        self.assertIn("metric", parameters["properties"])
        self.assertEqual(parameters["required"], ["metric"])

    def test_schema_sanitizer_drops_unsupported_keys_explicitly(self):
        sanitized = sanitize_json_schema(
            {
                "type": "object",
                "properties": {"metric": {"type": "string", "pattern": "^x$"}},
                "additionalProperties": False,
            }
        )

        self.assertNotIn("additionalProperties", sanitized)
        self.assertNotIn("pattern", sanitized["properties"]["metric"])


class GeminiProviderExecutionTest(unittest.IsolatedAsyncioTestCase):
    async def test_plan_parses_mocked_function_call(self):
        function_call = SimpleNamespace(name="rank_sections", args={"metric": "population_total", "order": "desc"})
        response = SimpleNamespace(function_calls=[function_call], text="")
        client = FakeClient([response])
        provider = GeminiProvider(api_key="test-key", client=client)

        result = await provider.plan(
            LLMPlanRequest(
                question="¿Cuál es la sección con mayor población?",
                system_prompt="",
                tools=[
                    LLMToolSchema(
                        name="rank_sections",
                        description="Rank sections",
                        parameters={"type": "object", "properties": {"metric": {"type": "string"}}},
                    )
                ],
            )
        )

        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.tool_call.tool_name, "rank_sections")
        self.assertEqual(result.tool_call.arguments["metric"], "population_total")
        self.assertEqual(result.confidence, "medium")
        self.assertEqual(client.models.calls[0]["model"], "gemini-2.5-flash-lite")

    async def test_plan_handles_no_function_call_gracefully(self):
        client = FakeClient([SimpleNamespace(function_calls=[], text="No tool")])
        provider = GeminiProvider(api_key="test-key", client=client)

        result = await provider.plan(
            LLMPlanRequest(
                question="Hola",
                system_prompt="",
                tools=[],
            )
        )

        self.assertIsNone(result.tool_call)
        self.assertEqual(result.confidence, "low")

    async def test_synthesize_parses_structured_answer(self):
        response = SimpleNamespace(
            text='{"answer":"La sección principal es Riviera Sur, con valor 1200.","suggested_followups":["¿Y en porcentaje?"],"caveats":["Estimación."]}'
        )
        provider = GeminiProvider(api_key="test-key", client=FakeClient([response]))

        result = await provider.synthesize(
            LLMSynthesisRequest(
                question="Pregunta",
                system_prompt="",
                tool_result={
                    "rows": [{"section_name": "Riviera Sur", "value": 1200}],
                    "summary": {},
                },
            )
        )

        self.assertEqual(result.answer, "La sección principal es Riviera Sur, con valor 1200.")
        self.assertEqual(result.suggested_followups, ["¿Y en porcentaje?"])
        self.assertEqual(result.caveats, ["Estimación."])

    async def test_synthesize_falls_back_to_plain_text_if_structured_missing(self):
        invalid_json = SimpleNamespace(text="Respuesta no JSON")
        plain_text = SimpleNamespace(text="Respuesta final en texto.")
        provider = GeminiProvider(api_key="test-key", client=FakeClient([invalid_json, plain_text]))

        result = await provider.synthesize(
            LLMSynthesisRequest(
                question="Pregunta",
                system_prompt="",
                tool_result={"summary": {}, "suggested_followups": ["Siguiente"]},
            )
        )

        self.assertEqual(result.answer, "Respuesta final en texto.")
        self.assertEqual(result.suggested_followups, ["Siguiente"])


class GeminiSecurityTest(unittest.TestCase):
    def test_frontend_files_do_not_reference_gemini_api_key(self):
        frontend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../soctrace-web"))
        matches = []
        for root, _, files in os.walk(frontend_root):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        if "GEMINI_API_KEY" in file.read():
                            matches.append(path)
                except UnicodeDecodeError:
                    continue

        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
