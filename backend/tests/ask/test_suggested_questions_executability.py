import unittest

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.conversation.conversational_policy import ConversationalPolicyLayer
from app.ask.sql import SqlValidator
from app.ask.suggestions import SuggestionRegistry, SuggestionValidator
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolRegistryV2, ToolResult, tool_call_from_operation
from app.ask.service import AskSocTraceService
from tests.ask.test_tools_v2 import FakeQueryExecutor


class SuggestedQuestionsExecutabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.query_executor = FakeQueryExecutor()
        self.registry = ToolRegistryV2(self.query_executor, SqlValidator(self.catalog.approved_relations), self.catalog)
        self.executor = ToolExecutorV2(self.registry)
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.validator = SuggestionValidator(
            registry=SuggestionRegistry(),
            tool_registry=self.registry,
            tool_executor=self.executor,
            operation_interpreter=self.interpreter,
        )

    def execute_question(self, question: str, last_party: str | None = None):
        operation = self.interpreter.interpret(question, municipio_id="29070", last_party=last_party)
        self.assertIsNotNone(operation)
        tool_call = tool_call_from_operation(operation)
        self.assertIsNotNone(tool_call)
        tool_name, args = tool_call
        result = self.executor.execute_sync(tool_name, args, ToolContext(municipio_id="29070", municipio_nombre="Mijas"))
        return tool_name, args, result

    def test_mobilizable_abstention_tool_executes_and_explains_score(self) -> None:
        tool_name, args, result = self.execute_question("¿Dónde hay más abstención movilizable?")

        self.assertEqual(tool_name, "mobilizable_abstention_opportunity")
        self.assertEqual(args["target"], "general")
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.rows)

        answer = AskSocTraceService._tool_v2_answer(object(), result)
        lower = answer.lower()
        self.assertIn("índice", lower)
        self.assertIn("0 a 1", lower)
        self.assertIn("no es una predicción individual", lower)
        self.assertIn("lectura estratégica por sección", lower)

    def test_mobilizable_abstention_does_not_inherit_party_on_standalone_question(self) -> None:
        tool_name, args, result = self.execute_question("¿Dónde hay más abstención movilizable?", last_party="PP")

        self.assertEqual(tool_name, "mobilizable_abstention_opportunity")
        self.assertEqual(args["target"], "general")
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.rows)
        answer = AskSocTraceService._tool_v2_answer(object(), result)
        self.assertIn("en términos generales", answer)
        self.assertNotIn("para PP", answer)

    def test_policy_does_not_inherit_left_bloc_context_for_standalone_mobilizable_abstention(self) -> None:
        decision = ConversationalPolicyLayer().resolve(
            "¿Dónde hay más abstención movilizable?",
            semantic_interpretation=None,
            conversation_context={
                "lastResult": {
                    "metadata": {
                        "components": [
                            {"metric": "abstention_pct"},
                            {"metric": "left_bloc_pct"},
                        ]
                    }
                }
            },
        )

        self.assertEqual(decision.preferred_tool, "mobilizable_abstention_opportunity")
        self.assertEqual(decision.preferred_arguments["target"], "general")

    def test_explicit_party_sets_mobilizable_abstention_target(self) -> None:
        tool_name, args, result = self.execute_question("¿Dónde hay más abstención movilizable para PSOE?", last_party="PP")

        self.assertEqual(tool_name, "mobilizable_abstention_opportunity")
        self.assertEqual(args["target"], "PSOE")
        answer = AskSocTraceService._tool_v2_answer(object(), result)
        self.assertIn("para PSOE", answer)

    def test_clear_followup_inherits_party_context(self) -> None:
        tool_name, args, result = self.execute_question("¿Y para ellos?", last_party="PSOE")

        self.assertEqual(tool_name, "mobilizable_abstention_opportunity")
        self.assertEqual(args["target"], "PSOE")
        self.assertEqual(result.status, "ok")

    def test_suggested_ctas_from_cross_metric_are_executable_after_validation(self) -> None:
        result = ToolResult(
            tool_name="cross_metric_ranking",
            operation="cross_metric_ranking",
            status="ok",
            rows=[{"section_id": "2907001007", "section_name": "Sección 07 · Cala de Mijas", "value": 0.806}],
            summary={"value_label": "Índice combinado"},
            metadata={
                "metric": "cross_metric_score",
                "components": [
                    {"metric": "abstention_pct", "direction": "high", "weight": 1.0},
                    {"metric": "left_bloc_pct", "direction": "high", "weight": 1.0},
                ],
            },
        )
        raw_ctas = AskSocTraceService._tool_v2_ctas(object(), result)
        service = AskSocTraceService.__new__(AskSocTraceService)
        service.suggestion_validator = self.validator
        service.sql_generator = type("SqlGeneratorStub", (), {"generate": lambda *args, **kwargs: None})()
        service._format_suggested_question = AskSocTraceService._format_suggested_question.__get__(service, AskSocTraceService)
        service._suggestion_context = AskSocTraceService._suggestion_context.__get__(service, AskSocTraceService)
        service._suggestion_is_executable = AskSocTraceService._suggestion_is_executable.__get__(service, AskSocTraceService)
        service._suggestion_fallback = AskSocTraceService._suggestion_fallback.__get__(service, AskSocTraceService)
        service._validated_ctas = AskSocTraceService._validated_ctas.__get__(service, AskSocTraceService)

        validated = service._validated_ctas(raw_ctas, None)

        self.assertTrue(validated)
        for cta in validated:
            validation = self.validator.validate(cta["question"], {"lastParty": "PP"})
            self.assertTrue(validation.valid, cta)
            self.assertNotEqual(validation.status, "empty")

    def test_available_registry_prompts_are_executable(self) -> None:
        for suggestion in SuggestionRegistry().all():
            if suggestion.context_required:
                continue
            with self.subTest(suggestion=suggestion.id):
                validation = self.validator.validate(suggestion.question, {})
                self.assertTrue(validation.valid, validation.model_dump())


if __name__ == "__main__":
    unittest.main()
