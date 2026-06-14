import unittest

from app.ask.llm import (
    LLMMessage,
    LLMPlanRequest,
    LLMProvider,
    LLMSynthesisRequest,
    LLMToolSchema,
    MockLLMProvider,
    ProviderNotConfiguredError,
    ProviderNotImplementedError,
    get_llm_provider,
)


class LLMProviderFactoryTest(unittest.TestCase):
    def test_factory_defaults_to_mock(self):
        provider = get_llm_provider()

        self.assertIsInstance(provider, MockLLMProvider)
        self.assertEqual(provider.name, "mock")

    def test_gemini_provider_requires_configuration(self):
        with self.assertRaises(ProviderNotConfiguredError):
            get_llm_provider("gemini")

    def test_openai_provider_is_not_implemented_yet(self):
        with self.assertRaises(ProviderNotImplementedError):
            get_llm_provider("openai")

    def test_provider_interface_imports_without_side_effects(self):
        provider = MockLLMProvider()

        self.assertIsInstance(provider, LLMProvider)


class MockLLMProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_mock_provider_plan_maps_largest_population(self):
        provider = MockLLMProvider()

        response = await provider.plan(
            LLMPlanRequest(
                question="¿Cuál es la sección con mayor población?",
                system_prompt="test",
            )
        )

        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.confidence, "high")
        self.assertIsNotNone(response.tool_call)
        self.assertEqual(response.tool_call.tool_name, "rank_sections")
        self.assertEqual(response.tool_call.arguments["metric"], "population_total")
        self.assertEqual(response.tool_call.arguments["order"], "desc")

    async def test_mock_provider_plan_maps_youngest_section(self):
        provider = MockLLMProvider()

        response = await provider.plan(
            LLMPlanRequest(
                question="¿Cuál es la sección más joven?",
                system_prompt="test",
            )
        )

        self.assertEqual(response.tool_call.tool_name, "rank_sections")
        self.assertEqual(response.tool_call.arguments["metric"], "average_age")
        self.assertEqual(response.tool_call.arguments["order"], "asc")

    async def test_mock_provider_plan_maps_retirees_proxy(self):
        provider = MockLLMProvider()

        response = await provider.plan(
            LLMPlanRequest(
                question="¿Qué secciones concentran más jubilados?",
                system_prompt="test",
            )
        )

        self.assertEqual(response.tool_call.tool_name, "rank_sections")
        self.assertEqual(response.tool_call.arguments["metric"], "population_over_65")

    async def test_mock_provider_plan_maps_persistent_winner(self):
        provider = MockLLMProvider()

        response = await provider.plan(
            LLMPlanRequest(
                question="¿Dónde gana siempre el PP?",
                system_prompt="test",
            )
        )

        self.assertEqual(response.tool_call.tool_name, "persistent_winner")
        self.assertEqual(response.tool_call.arguments["party"], "PP")

    async def test_mock_provider_synthesize_uses_summary_answer(self):
        provider = MockLLMProvider()

        response = await provider.synthesize(
            LLMSynthesisRequest(
                question="Pregunta",
                system_prompt="test",
                tool_result={
                    "summary": {"answer": "Respuesta preparada."},
                    "suggested_followups": ["Otra pregunta"],
                    "caveats": ["Caveat"],
                },
            )
        )

        self.assertEqual(response.answer, "Respuesta preparada.")
        self.assertEqual(response.suggested_followups, ["Otra pregunta"])
        self.assertEqual(response.caveats, ["Caveat"])

    async def test_mock_provider_synthesize_returns_generic_answer(self):
        provider = MockLLMProvider()

        response = await provider.synthesize(
            LLMSynthesisRequest(
                question="Pregunta",
                system_prompt="test",
                tool_result={"summary": {}},
            )
        )

        self.assertIn("proveedor LLM real", response.answer)

    def test_healthcheck_reports_provider_and_configuration(self):
        health = MockLLMProvider().healthcheck()

        self.assertEqual(health["provider"], "mock")
        self.assertTrue(health["configured"])
        self.assertEqual(health["models"], {})

    def test_mock_requires_no_api_keys(self):
        health = get_llm_provider("mock").healthcheck()

        self.assertTrue(health["configured"])


class LLMProviderSchemaTest(unittest.TestCase):
    def test_schemas_validate_correctly(self):
        message = LLMMessage(role="user", content="Hola")
        tool = LLMToolSchema(
            name="rank_sections",
            description="Rank sections",
            parameters={"type": "object", "properties": {}},
        )
        plan_request = LLMPlanRequest(
            question="¿Cuál es la sección más joven?",
            system_prompt="Sistema",
            conversation_context={"last_tool": "rank_sections"},
            semantic_context={"operation": "rank_sections"},
            tools=[tool],
            complexity="simple",
        )

        self.assertEqual(message.role, "user")
        self.assertEqual(plan_request.tools[0].name, "rank_sections")


if __name__ == "__main__":
    unittest.main()
