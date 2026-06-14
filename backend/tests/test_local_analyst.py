import unittest
from types import SimpleNamespace

from app.ask.conversation import ConversationState
from app.ask.conversation import conversation_store
from app.ask.conversation.conversation_state import ActiveElection, AgeRange, ConversationSection
from app.ask.interpreter import QuestionInterpreter
from app.ask.planner import SocTracePlanner
from app.ask.sql import SqlGenerator
from app.ask.sql.sql_validator import ValidationResult
from app.ask.reference_resolver import resolve_references
from app.ask.service import AskSocTraceService, CONVERSATION_STATE
from app.schemas.ask import AskRequest
from app.services.local_analyst_service import DHondtCalculator, IntentRouter, ToolPlanner


class IntentRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()

    def test_detects_required_intents(self) -> None:
        cases = {
            "Calcula los cocientes D'Hondt del PSOE": "electoral_calculation",
            "Calcula los cocientes D Hondt del PSOE": "electoral_calculation",
            "Compara la participacion entre 2019 y 2023": "section_comparison",
            "Explica la metodologia del forecast": "methodology_explanation",
            "Cual es la prevision para 2027": "forecast_question",
            "Donde es mas fuerte el PSOE": "simple_electoral_ranking",
            "¿En qué elecciones el PP sacó menos porcentaje de voto en la sección 36 La Sierrezuela?": "party_performance_by_section_across_elections",
            "¿Cuál fue el mejor resultado del PSOE en la sección 12?": "party_performance_by_section_across_elections",
            "Evolución de VOX en La Sierrezuela": "party_performance_by_section_across_elections",
            "¿Dónde sacó más voto el PP en 2023?": "simple_electoral_ranking",
            "¿A quién suelen votar históricamente en la sección más joven?": "historical_party_dominance_for_section",
            "Genial, y a quien suelen votar históricamente?": "historical_party_dominance_for_section",
            "Necesito una lectura estrategica": "strategic_interpretation",
            "Que tiempo hace hoy": "unknown_or_unsupported",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(self.router.detect(question), expected)

    def test_unknown_does_not_plan_an_internal_tool(self) -> None:
        self.assertEqual(ToolPlanner().plan("unknown_or_unsupported"), [])


class DHondtCalculatorTest(unittest.TestCase):
    def test_assigns_seats_from_ranked_quotients(self) -> None:
        result = DHondtCalculator().calculate(
            [
                {"party": "A", "votes": 1000},
                {"party": "B", "votes": 600},
                {"party": "C", "votes": 200},
            ],
            total_seats=5,
            threshold_pct=5,
        )
        self.assertEqual(result["seats"], {"A": 3, "B": 2})
        self.assertEqual([(item.party, item.divisor) for item in result["winners"]], [
            ("A", 1),
            ("B", 1),
            ("A", 2),
            ("A", 3),
            ("B", 2),
        ])


class QuestionInterpreterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.interpreter = QuestionInterpreter()

    def test_acceptance_questions_produce_expected_intents(self) -> None:
        cases = {
            "Which is youngest section?": ("single_extreme", "section", "average_age", "min", None),
            "¿Cuál es la sección más joven?": ("single_extreme", "section", "average_age", "min", None),
            "¿Cuál es la sección con mayor número de jóvenes?": ("single_extreme", "section", "population_under_30", "max", None),
            "¿Cuál es la sección más envejecida?": ("single_extreme", "section", "average_age", "max", None),
            "¿Qué sección tiene más población?": ("single_extreme", "section", "population_total", "max", None),
            "¿Cuál es la sección con menor renta?": ("single_extreme", "section", "income_individual", "min", None),
            "¿Dónde hay más abstención?": ("single_extreme", "section", "abstention_pct", "max", None),
            "¿Dónde es más fuerte el PP?": ("single_extreme", "section", "vote_pct", "max", "PP"),
            "¿En qué secciones gana siempre el PSOE?": ("derived_metric", "section", "persistent_winner", "max", "PSOE"),
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                intent = self.interpreter.interpret(question)
                self.assertEqual(intent.intent, expected[0])
                self.assertEqual(intent.entity, expected[1])
                self.assertEqual(intent.metric, expected[2])
                self.assertEqual(intent.direction, expected[3])
                self.assertEqual(intent.confidence, "high")
                self.assertEqual(intent.filters.get("municipality"), "Mijas")
                if expected[4]:
                    self.assertEqual(intent.filters.get("party"), expected[4])

    def test_sql_generator_uses_interpreted_youngest_section_intent(self) -> None:
        question = "Which is youngest section?"
        intent = self.interpreter.interpret(question)
        plan = SqlGenerator().generate(question, analytical_intent=intent, active_municipality="29070")
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.intent, "section_metric_extreme")
        self.assertIn("marts.agent_section_profile", plan.sql)
        self.assertNotIn("marts.ask_section_profile", plan.sql)
        self.assertIn("ORDER BY average_age ASC", plan.sql)
        self.assertIn("LIMIT 1", plan.sql)

    def test_sql_generator_distinguishes_youngest_from_most_young_people(self) -> None:
        generator = SqlGenerator()
        youngest = generator.generate(
            "¿Cuál es la sección más joven?",
            analytical_intent=self.interpreter.interpret("¿Cuál es la sección más joven?"),
            active_municipality="29070",
        )
        most_young = generator.generate(
            "¿Cuál es la sección con mayor número de jóvenes?",
            analytical_intent=self.interpreter.interpret("¿Cuál es la sección con mayor número de jóvenes?"),
            active_municipality="29070",
        )
        self.assertIsNotNone(youngest)
        self.assertIsNotNone(most_young)
        assert youngest is not None and most_young is not None
        self.assertIn("average_age", youngest.sql)
        self.assertIn("population_under_30", most_young.sql)
        self.assertIn("marts.agent_section_profile", most_young.sql)
        self.assertNotIn("marts.ask_section_profile", most_young.sql)
        self.assertNotEqual(youngest.sql, most_young.sql)


class _AlwaysOkValidator:
    def validate(self, sql: str) -> ValidationResult:
        return ValidationResult(True)


class _GoldenQueryExecutor:
    def execute(self, sql: str) -> list[dict]:
        if "marts.ask_section_profile" in sql or "marts.agent_section_profile" in sql:
            if "population_under_30_pct" in sql:
                return [
                    {
                        "section_id": "2907001009",
                        "section_name": "Sección 9 · Calahonda Norte",
                        "municipio_nombre": "Mijas",
                        "population_under_30_pct": 34.4,
                        "year": 2023,
                    }
                ]
            if "population_under_30" in sql:
                return [
                    {
                        "section_id": "2907001023",
                        "section_name": "Sección 23 · Riviera Sur",
                        "municipio_nombre": "Mijas",
                        "population_under_30": 1503,
                        "year": 2023,
                    },
                    {
                        "section_id": "2907001018",
                        "section_name": "Sección 18 · Camino Campanales",
                        "municipio_nombre": "Mijas",
                        "population_under_30": 1180,
                        "year": 2023,
                    },
                ]
            if "average_age" in sql:
                return [
                    {
                        "section_id": "2907001025",
                        "section_name": "Sección 25 · María Zambrano Este",
                        "municipio_nombre": "Mijas",
                        "average_age": 32.91,
                        "year": 2023,
                    }
                ]
            if "population_total" in sql:
                return [
                    {
                        "section_id": "2907001023",
                        "section_name": "Sección 23 · Riviera Sur",
                        "municipio_nombre": "Mijas",
                        "population_total": 4787,
                        "year": 2023,
                    }
                ]
        if "population_under_30" in sql:
            if "population_under_30_pct DESC" in sql:
                return [
                    {
                        "section_id": "2907001009",
                        "section_name": "Sección 9 · Calahonda Norte",
                        "population_under_30": 410,
                        "population_under_30_pct": 34.4,
                        "total_population": 1192,
                        "year": 2023,
                    }
                ]
            return [
                {
                    "section_id": "2907001023",
                    "section_name": "Sección 23 · Riviera Sur",
                    "population_under_30": 1503,
                    "population_under_30_pct": 31.4,
                    "total_population": 4787,
                    "year": 2023,
                },
                {
                    "section_id": "2907001018",
                    "section_name": "Sección 18 · Camino Campanales",
                    "population_under_30": 1180,
                    "population_under_30_pct": 30.2,
                    "total_population": 3907,
                    "year": 2023,
                },
                {
                    "section_id": "2907001030",
                    "section_name": "Sección 30 · Las Lagunas Centro",
                    "population_under_30": 980,
                    "population_under_30_pct": 29.8,
                    "total_population": 3289,
                    "year": 2023,
                }
            ]
        if "population_over_65" in sql:
            return [
                {
                    "section_id": "2907001011",
                    "section_name": "Sección 11 · Centro Histórico",
                    "population_over_65": 520,
                    "population_over_65_pct": 31.2,
                    "total_population": 1667,
                    "year": 2023,
                }
            ]
        if "party_summary" in sql:
            return [
                {
                    "section_id": "2907001025",
                    "section_name": "Sección 25 · María Zambrano Este",
                    "canonical_party": "PP",
                    "average_vote_pct": 26.1,
                    "first_place_count": 5,
                    "total_votes": 1234,
                    "elections_included": 12,
                    "first_year": 2011,
                    "last_year": 2023,
                    "historical_rank": 1,
                }
            ]
        if "marts.v_mapa_age_structure_2023" in sql:
            return [
                {
                    "section_id": "2907001025",
                    "section_name": "Sección 25 · María Zambrano Este",
                    "average_age": 32.91,
                    "year": 2023,
                }
            ]
        if "marts.v_mapa_age_structure age" in sql:
            return [
                {
                    "year": 2021,
                    "target_section_id": "2907001025",
                    "target_section_name": "Sección 25 · María Zambrano Este",
                    "target_average_age": 32.52,
                    "target_rank": 1,
                    "youngest_section_id": "2907001025",
                    "youngest_section_name": "Sección 25 · María Zambrano Este",
                    "youngest_average_age": 32.52,
                    "target_is_extreme": True,
                    "years_checked": 2,
                    "years_as_extreme": 2,
                },
                {
                    "year": 2023,
                    "target_section_id": "2907001025",
                    "target_section_name": "Sección 25 · María Zambrano Este",
                    "target_average_age": 32.91,
                    "target_rank": 1,
                    "youngest_section_id": "2907001025",
                    "youngest_section_name": "Sección 25 · María Zambrano Este",
                    "youngest_average_age": 32.91,
                    "target_is_extreme": True,
                    "years_checked": 2,
                    "years_as_extreme": 2,
                },
            ]
        if "party_wins" in sql and "elections_checked" in sql:
            return [
                {
                    "section_id": "2907001004",
                    "section_name": "Sección 04 · Centro Salud",
                    "elections_checked": 12,
                    "party_wins": 12,
                    "win_rate_pct": 100.0,
                    "always_wins": True,
                },
                {
                    "section_id": "2907001007",
                    "section_name": "Sección 07 · Cala de Mijas",
                    "elections_checked": 12,
                    "party_wins": 12,
                    "win_rate_pct": 100.0,
                    "always_wins": True,
                },
                {
                    "section_id": "2907001010",
                    "section_name": "Sección 10 · El Coto / Lagarejo",
                    "elections_checked": 12,
                    "party_wins": 12,
                    "win_rate_pct": 100.0,
                    "always_wins": True,
                },
                {
                    "section_id": "2907001011",
                    "section_name": "Sección 11 · Centro Histórico",
                    "elections_checked": 12,
                    "party_wins": 9,
                    "win_rate_pct": 75.0,
                    "always_wins": False,
                }
            ]
        if "age_range_population" in sql:
            return [
                {
                    "section_id": "2907001025",
                    "section_name": "Sección 25 · María Zambrano Este",
                    "age_range_population": 300,
                    "abstention_pct": 35.0,
                    "participation_pct": 65.0,
                    "estimated_abstainers": 105,
                    "estimated_voters": 195,
                    "municipality_age_range_population": 2000,
                    "municipality_estimated_abstainers": 700,
                    "municipality_estimated_voters": 1300,
                }
            ]
        return []


class AskSocTraceAgentLoopGoldenTest(unittest.TestCase):
    def setUp(self) -> None:
        conversation_store._states.clear()
        self.service = AskSocTraceService.__new__(AskSocTraceService)
        self.service.settings = SimpleNamespace(app_env="test", openai_api_key=None, openai_model="test")
        self.service.sql_generator = SqlGenerator()
        self.service.sql_validator = _AlwaysOkValidator()
        self.service.query_executor = _GoldenQueryExecutor()
        self.service.question_interpreter = QuestionInterpreter()
        self.service.planner = SocTracePlanner()
        self.service._resolved_references = {}
        self.service._analytical_intent = None
        self.service._deterministic_match = None

    def _ask_agent(self, question: str):
        payload = AskRequest(question=question, conversationId="golden", activeMunicipality="29070")
        state = conversation_store.get_or_create("golden", "29070")
        self.service._resolved_references = resolve_references(question, state)
        self.service._deterministic_match = self.service.question_interpreter.deterministic_match(question)
        self.service._analytical_intent = self.service._deterministic_match or self.service.question_interpreter.interpret(
            question,
            self.service.sql_generator.catalog,
        )
        response = self.service._run_agent_loop(payload, state)
        self.assertIsNotNone(response)
        return response

    def test_three_turn_youngest_conversation_uses_new_plans(self) -> None:
        first = self._ask_agent("Cuál es la sección más joven?")
        first_plan = first.data["executionPlan"]
        self.assertEqual(first_plan["task"], "single_extreme")
        self.assertEqual(first_plan["renderer"], "singleExtremeRenderer")
        self.assertIn("average_age", first.table["columns"])
        self.assertNotIn("Cohorte total", first.answer)

        second = self._ask_agent("Siempre ha sido la sección más joven?")
        second_plan = second.data["executionPlan"]
        self.assertEqual(second_plan["task"], "historical_extreme_consistency")
        self.assertEqual(second_plan["renderer"], "historicalConsistencyRenderer")
        self.assertIn("target_average_age", second.table["columns"])
        self.assertIn("años disponibles", second.answer)
        self.assertNotEqual(second.answer, first.answer)

        third = self._ask_agent("Cuál es el partido históricamente más votado en la sección más joven?")
        third_plan = third.data["executionPlan"]
        self.assertEqual(third_plan["task"], "historical_party_dominance_for_section")
        self.assertEqual(third_plan["renderer"], "partyHistoryRenderer")
        self.assertIn("canonical_party", third.table["columns"])
        self.assertNotEqual(third.answer, first.answer)

    def test_young_people_followup_switches_to_percentage(self) -> None:
        first = self._ask_agent("Cuál es la sección más joven?")
        self.assertEqual(first.data["executionPlan"]["resolvedContext"]["metric"], "average_age")

        second = self._ask_agent("Cuál es la sección con mayor número de jóvenes?")
        second_plan = second.data["executionPlan"]
        self.assertEqual(second_plan["resolvedContext"]["metric"], "population_under_30")
        self.assertIn("menores de 30", second.answer)
        self.assertIn("population_under_30", second.table["columns"])
        self.assertNotIn("PLAN -> EXECUTE", second.methodology)

        third = self._ask_agent("¿Y en porcentaje?")
        third_plan = third.data["executionPlan"]
        self.assertEqual(third_plan["resolvedContext"]["metric"], "population_under_30_pct")
        self.assertIn("mayor porcentaje de jóvenes", third.answer)
        self.assertIn("population_under_30_pct", third.table["columns"])

    def test_default_simple_mode_and_previous_detail_mode(self) -> None:
        first = self.service.ask(AskRequest(question="Cuál es la sección con mayor número de jóvenes?", conversationId="golden", activeMunicipality="29070"))
        self.assertEqual(first.mode, "simple")
        self.assertIn("menores de 30", first.answer)

        table_response = self.service.ask(AskRequest(question="Dame la tabla", conversationId="golden", activeMunicipality="29070"))
        self.assertEqual(table_response.mode, "detailed")
        self.assertEqual(table_response.data, {"fromPreviousContext": True})
        self.assertIsNotNone(table_response.table)
        assert table_response.table is not None
        self.assertIn("population_under_30", table_response.table["columns"])

        methodology_response = self.service.ask(AskRequest(question="¿Cómo lo has calculado?", conversationId="golden", activeMunicipality="29070"))
        self.assertEqual(methodology_response.mode, "detailed")
        self.assertIn("Así lo he calculado", methodology_response.answer)

    def test_party_history_for_youngest_section_without_previous_context(self) -> None:
        response = self._ask_agent("A quién suelen votar históricamente en la sección más joven?")
        plan = response.data["executionPlan"]
        self.assertEqual(plan["task"], "historical_party_dominance_for_section")
        self.assertEqual(plan["renderer"], "partyHistoryRenderer")
        self.assertIn("canonical_party", response.table["columns"])
        self.assertIn("históricamente", response.answer)
        self.assertNotIn("edad media de 32", response.answer)

    def test_psoe_always_wins_uses_agent_check(self) -> None:
        response = self._ask_agent("En qué secciones gana el PSOE siempre?")
        plan = response.data["executionPlan"]
        self.assertEqual(plan["task"], "aggregation")
        self.assertEqual(plan["renderer"], "rankingRenderer")
        self.assertIn("elections_checked", response.table["columns"])
        self.assertEqual(response.resultType, "entity_list")
        self.assertEqual(len(response.entities), 3)
        self.assertIn("El PSOE gana", response.answer)
        self.assertIn("Sección 04 · Centro Salud", response.entities[0]["name"])
        self.assertNotIn("partido consultado", response.answer)
        self.assertNotIn("290700", response.answer)
        self.assertNotIn("Cohorte total", response.answer)

    def test_young_population_plural_question_returns_entities(self) -> None:
        response = self._ask_agent("Qué secciones tienen más población joven?")
        plan = response.data["executionPlan"]
        self.assertEqual(plan["renderer"], "rankingRenderer")
        self.assertEqual(response.resultType, "entity_list")
        self.assertGreaterEqual(len(response.entities), 2)
        self.assertIn("Las secciones con más población joven", response.answer)
        self.assertIn("Riviera Sur", response.entities[0]["name"])
        self.assertNotIn("core.poblacion_edad", response.answer)

    def test_age_abstention_semantic_sql_is_agent_planned(self) -> None:
        response = self._ask_agent("Cuántas personas mayores de 65 años se abstuvieron en las municipales de 2023?")
        plan = response.data["executionPlan"]
        self.assertEqual(plan["task"], "aggregation")
        self.assertEqual(plan["renderer"], "rankingRenderer")
        self.assertIn("age_range_population", response.table["columns"])
        self.assertNotIn("Sección 25 · María Zambrano Este, con una edad media", response.answer)


class AskSocTraceCompositeRoutingTest(unittest.TestCase):
    def setUp(self) -> None:
        CONVERSATION_STATE.clear()
        self.service = AskSocTraceService.__new__(AskSocTraceService)
        self.service.planner = SocTracePlanner()

    def test_prefers_age_abstention_composite_tool(self) -> None:
        payload = AskRequest(
            question=(
                "Quiero que calcules número de personas que tenían de 18 a 22 años en 2023 "
                "en cada una de las secciones y, en base al % de abstención, ordénalo de mayor a menor."
            ),
            conversationId="test",
            activeMunicipality="29070",
        )
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        self.assertEqual(
            self.service._resolve_age_abstention_params(payload),
            {
                "municipality": "29070",
                "year": 2023,
                "electionType": "municipales",
                "minAge": 18,
                "maxAge": 22,
                "groupBy": "section",
                "sortBy": "estimated_abstainers",
                "sortDirection": "desc",
            },
        )

    def test_routes_open_ended_senior_abstention_question(self) -> None:
        payload = AskRequest(
            question="¿Cuántas personas mayores de 65 años se abstuvieron de votar en 2023 en Mijas en las elecciones municipales?",
            conversationId="senior",
            activeMunicipality="29070",
        )
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        params = self.service._resolve_age_abstention_params(payload)
        self.assertEqual(params["minAge"], 65)
        self.assertIsNone(params["maxAge"])
        self.assertEqual(params["year"], 2023)
        self.assertEqual(params["electionType"], "municipales")

    def test_routes_senior_no_votaron_short_question(self) -> None:
        payload = AskRequest(
            question="¿Cuántos mayores de 65 no votaron en las municipales de 2023?",
            conversationId="senior-short",
            activeMunicipality="29070",
        )
        params = self.service._resolve_age_abstention_params(payload)
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        self.assertEqual(params["minAge"], 65)
        self.assertIsNone(params["maxAge"])

    def test_routes_under_30_abstention_question(self) -> None:
        payload = AskRequest(
            question="¿Cuántos menores de 30 se abstuvieron en las municipales de 2023?",
            conversationId="under-30",
            activeMunicipality="29070",
        )
        params = self.service._resolve_age_abstention_params(payload)
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        self.assertEqual(params["minAge"], 0)
        self.assertEqual(params["maxAge"], 29)

    def test_routes_senior_section_ranking_without_explicit_year(self) -> None:
        payload = AskRequest(
            question="Ordena por sección la abstención estimada de personas mayores de 65 años.",
            conversationId="senior-ranking",
            activeMunicipality="29070",
        )
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        params = self.service._resolve_age_abstention_params(payload)
        self.assertEqual(params["minAge"], 65)
        self.assertIsNone(params["maxAge"])
        self.assertEqual(params["year"], 2023)

    def test_follow_up_reuses_last_resolved_age_range(self) -> None:
        CONVERSATION_STATE["thread-1"] = ConversationState(
            conversationId="thread-1",
            municipality="29070",
            activeYear=2023,
            activeElection=ActiveElection(type="municipales", year=2023),
            lastAgeRange=AgeRange(minAge=18, maxAge=22),
        )
        payload = AskRequest(
            question=(
                "De esas personas, ¿cuántas crees que fueron a votar? "
                "Calcula en base a la abstención por secciones."
            ),
            conversationId="thread-1",
            activeMunicipality="29070",
        )
        self.assertTrue(self.service._should_use_age_abstention_tool(payload))
        params = self.service._resolve_age_abstention_params(payload)
        self.assertEqual(params["minAge"], 18)
        self.assertEqual(params["maxAge"], 22)
        self.assertEqual(params["electionType"], "municipales")

    def test_follow_up_builds_winner_party_plan_for_previous_sections(self) -> None:
        CONVERSATION_STATE["thread-2"] = ConversationState(
            conversationId="thread-2",
            municipality="29070",
            activeElection=ActiveElection(type="municipales", year=2023),
            lastSections=[
                ConversationSection(sectionId="2907001023", sectionName="Sección 23 · Riviera Sur"),
                ConversationSection(sectionId="2907001036", sectionName="Sección 36 · Sierrezuela"),
            ],
        )
        payload = AskRequest(
            question="¿En cuántas de esas secciones el PP fue la fuerza más votada?",
            conversationId="thread-2",
            activeMunicipality="29070",
        )
        state = self.service._ensure_state(payload)
        resolved = __import__("app.ask.reference_resolver", fromlist=["resolve_references"]).resolve_references(payload.question, state)
        plan = self.service.planner.build_plan(payload.question, resolved, payload.activeMunicipality)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.intent, "count_winner_party_in_previous_sections")
        self.assertEqual(plan.steps[1].toolName, "winner_party_by_section_set")

    def test_follow_up_builds_income_and_age_plans(self) -> None:
        CONVERSATION_STATE["thread-3"] = ConversationState(
            conversationId="thread-3",
            municipality="29070",
            lastSections=[ConversationSection(sectionId="2907001023", sectionName="Sección 23 · Riviera Sur")],
        )
        state = CONVERSATION_STATE["thread-3"]
        resolved_income = __import__("app.ask.reference_resolver", fromlist=["resolve_references"]).resolve_references(
            "¿Cuál es la renta media de esas secciones?",
            state,
        )
        income_plan = self.service.planner.build_plan(
            "¿Cuál es la renta media de esas secciones?",
            resolved_income,
            "29070",
        )
        self.assertEqual(income_plan.intent, "average_income_previous_sections")
        resolved_age = __import__("app.ask.reference_resolver", fromlist=["resolve_references"]).resolve_references(
            "¿Y qué edad media tienen?",
            state,
        )
        age_plan = self.service.planner.build_plan("¿Y qué edad media tienen?", resolved_age, "29070")
        self.assertEqual(age_plan.intent, "average_age_previous_sections")


if __name__ == "__main__":
    unittest.main()
