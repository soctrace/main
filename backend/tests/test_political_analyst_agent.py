import asyncio
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.analyst.agent import _is_grounded_synthesis, get_political_analyst_agent
from app.services.analyst.agent import PoliticalAnalystAgent
from app.services.analyst.composer import compose_final_answer
from app.services.analyst.conversation_intelligence import ConversationIntelligenceLayer
from app.services.analyst.executive_reasoning import ExecutiveReasoningLayer
from app.services.analyst.planner import PoliticalPlanner
from app.services.analyst.political_rules import PoliticalClassificationEngine
from app.services.analyst.schemas import AnalystChatRequest, AnalystChatResponse
from app.services.analyst.tools import AnalystToolResult
from app.services.analyst.workflows import PoliticalAnalystWorkflowExecutor


class PoliticalClassificationEngineTest(unittest.TestCase):
    def test_classifies_opportunity_without_false_swing_when_margin_is_not_close(self) -> None:
        tags = PoliticalClassificationEngine().classify(
            {
                "winning_party": "PP",
                "winning_party_pct": 41.1,
                "runner_up_pct": 25.2,
                "victory_margin_pct": 15.9,
                "abstention_rate_pct": 58.4,
                "under_30_pct": 23.9,
                "individual_income": 14415,
                "opportunity_score": 103.5,
            }
        )

        self.assertIn("Conservative Stronghold", tags)
        self.assertIn("High Abstention Area", tags)
        self.assertIn("Mobilization Opportunity", tags)
        self.assertNotIn("Swing Section", tags)

    def test_classifies_true_swing_section_from_victory_margin(self) -> None:
        tags = PoliticalClassificationEngine().classify(
            {
                "winning_party": "PSOE",
                "winning_party_pct": 32.0,
                "runner_up_pct": 29.0,
                "victory_margin_pct": 3.0,
                "abstention_rate_pct": 40.0,
                "opportunity_score": 72.0,
            }
        )

        self.assertIn("Swing Section", tags)
        self.assertIn("Persuasion Opportunity", tags)


class PoliticalAnalystAgentResponseTest(unittest.TestCase):
    def test_builds_phase_one_response_contract_from_tool_rows(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        tool_result = AnalystToolResult(
            name="rank_sections_by_opportunity",
            rows=[
                {
                    "section_id": "2907001017",
                    "section_name": "Sección 17 · Campo Mijas",
                    "winning_party": "PP",
                    "winning_party_pct": 34.97,
                    "runner_up_pct": 28.11,
                    "victory_margin_pct": 6.87,
                    "target_party_vote_pct": 34.97,
                    "abstention_rate_pct": 50.09,
                    "under_30_pct": 34.96,
                    "individual_income": 14861,
                    "opportunity_score": 103.5,
                }
            ],
            data_used=["marts.mv_electoral_behavior"],
            methodology="Ranking determinista de oportunidad.",
            warnings=[],
        )

        response = asyncio.run(
            agent._build_response(
                intent="opportunity",
                message="Where can PP grow?",
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=tool_result,
            )
        )

        self.assertEqual(response.confidence, "high")
        self.assertEqual(response.conversation_id, "test-conversation")
        self.assertEqual(response.data_used, ["marts.mv_electoral_behavior"])
        self.assertEqual(response.sections[0].section_id, "2907001017")
        self.assertTrue(response.tables)
        self.assertTrue(response.charts)
        self.assertTrue(response.strategic_recommendations)
        self.assertEqual(response.synthetic_variables_used[0].name, "turnout_opportunity_score")


class PoliticalPlannerWorkflowTest(unittest.TestCase):
    def test_conversation_intelligence_suggested_questions_needs_no_tools(self) -> None:
        intelligence = ConversationIntelligenceLayer().classify("sugiereme preguntas para hacerte")

        self.assertEqual(intelligence.conversation_type, "conversational")
        self.assertFalse(intelligence.requires_data)
        self.assertTrue(intelligence.should_answer_without_tools)

    def test_conversational_chat_suggests_questions_without_data_insufficiency(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )

        response = asyncio.run(
            agent.chat(AnalystChatRequest(message="sugiereme preguntas para hacerte", municipality_id="29070"))
        )

        self.assertIn("Estrategia electoral", response.answer)
        self.assertIn("¿Dónde puede crecer el PP en Mijas?", response.answer)
        self.assertNotIn("insuficiente", response.answer.lower())
        self.assertEqual(response.data_used, [])
        self.assertLessEqual(len(response.follow_up_questions), 3)

    def test_exact_questions_prompt_bypasses_planner_workflows_and_tools(self) -> None:
        class _FailingPlanner:
            def plan(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("planner should not be called")

        class _FailingWorkflowExecutor:
            def run(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("workflow should not be called")

        question = "Dime qué preguntas puedo hacerte"
        intelligence = ConversationIntelligenceLayer().classify(question)
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.planner = _FailingPlanner()
        agent.workflow_executor = _FailingWorkflowExecutor()

        response = asyncio.run(agent.chat(AnalystChatRequest(message=question, municipality_id="29070")))

        self.assertEqual(intelligence.conversation_type, "conversational")
        self.assertTrue(intelligence.should_answer_without_tools)
        self.assertIn("Estrategia electoral", response.answer)
        self.assertIn("Servicios públicos", response.answer)
        self.assertEqual(response.display_mode, "chat")
        self.assertEqual(response.data_used, [])
        self.assertEqual(response.tables, [])
        self.assertEqual(response.methodology, "")
        self.assertEqual(response.warnings, [])
        self.assertEqual(response.limitations, [])

    def test_greeting_is_conversational_without_planner_workflow_or_tools(self) -> None:
        class _FailingPlanner:
            def plan(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("planner should not be called")

        class _FailingWorkflowExecutor:
            def run(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("workflow should not be called")

        intelligence = ConversationIntelligenceLayer().classify("hola")
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.planner = _FailingPlanner()
        agent.workflow_executor = _FailingWorkflowExecutor()

        response = asyncio.run(agent.chat(AnalystChatRequest(message="hola", municipality_id="29070")))

        self.assertEqual(intelligence.conversation_type, "conversational")
        self.assertTrue(intelligence.should_answer_without_tools)
        self.assertFalse(intelligence.requires_data)
        self.assertIn("Hola. Soy Ask soctrace", response.answer)
        self.assertEqual(response.tools_used, [])
        self.assertEqual(response.tables, [])
        self.assertNotIn("Sí. Para una decisión territorial general", response.answer)
        self.assertNotIn("Zonas a revisar primero", response.answer)

    def test_unknown_input_asks_clarification_without_workflow_or_territorial_ranking(self) -> None:
        class _FailingWorkflowExecutor:
            def run(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("workflow should not be called")

        question = "asdf qwer zzz"
        plan = PoliticalPlanner().plan(question, "29070")
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.workflow_executor = _FailingWorkflowExecutor()

        response = asyncio.run(agent.chat(AnalystChatRequest(message=question, municipality_id="29070")))

        self.assertEqual(plan.goal, "unknown_or_conversational")
        self.assertTrue(plan.needs_clarification)
        self.assertIn("¿Qué tema quieres explorar primero?", response.answer)
        self.assertEqual(response.tools_used, [])
        self.assertEqual(response.tables, [])
        self.assertNotIn("Sí. Para una decisión territorial general", response.answer)
        self.assertNotIn("Zonas a revisar primero", response.answer)

    def test_metric_questions_classify_and_plan_as_analytical_goals(self) -> None:
        population_question = "¿Cuál es la sección con mayor población?"
        elderly_question = "¿Cuál es la sección con mayor número de personas mayores?"

        population_intelligence = ConversationIntelligenceLayer().classify(population_question)
        elderly_intelligence = ConversationIntelligenceLayer().classify(elderly_question)
        population_plan = PoliticalPlanner().plan(population_question, "29070")
        elderly_plan = PoliticalPlanner().plan(elderly_question, "29070")

        self.assertEqual(population_intelligence.conversation_type, "analytical")
        self.assertEqual(population_intelligence.user_intent, "population_max_section")
        self.assertEqual(population_plan.goal, "population_max_section")
        self.assertEqual(population_plan.domain, "demographic_analysis")
        self.assertNotEqual(population_plan.goal, "general_territorial_advice")

        self.assertEqual(elderly_intelligence.conversation_type, "analytical")
        self.assertEqual(elderly_intelligence.user_intent, "elderly_population_max_section")
        self.assertEqual(elderly_plan.goal, "elderly_population_max_section")
        self.assertEqual(elderly_plan.domain, "demographic_analysis")
        self.assertNotEqual(elderly_plan.goal, "demographic_targeting")

    def test_ambiguous_change_plans_as_clarification_not_general_territorial(self) -> None:
        question = "¿Qué secciones cambiaron más entre 2019 y 2023?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertEqual(intelligence.conversation_type, "analytical")
        self.assertEqual(intelligence.user_intent, "change_between_years")
        self.assertEqual(plan.goal, "ambiguous_change_between_years")
        self.assertTrue(plan.needs_clarification)
        self.assertIn("cambio demográfico", plan.clarification_question or "")
        self.assertNotEqual(plan.goal, "general_territorial_advice")

    def test_population_max_question_uses_direct_metric_lookup(self) -> None:
        class _FailingPlanner:
            def plan(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("planner should not be called")

        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.tools = _FakePoliticalTools()
        agent.planner = _FailingPlanner()

        response = asyncio.run(
            agent.chat(AnalystChatRequest(message="¿Cuál es la sección con mayor población?", municipality_id="29070"))
        )

        self.assertIn("intent=population_max_section", response.methodology)
        self.assertIn("workflow=demographic_metric_lookup", response.methodology)
        self.assertIn("no fallback workflow activated", response.methodology)
        self.assertEqual(response.tools_used, ["get_population_ranking"])
        self.assertIn("Sección 23 · Riviera Sur", response.answer)
        self.assertIn("5.351", response.answer)
        self.assertIn("2025", response.answer)
        self.assertNotIn("promocion", response.answer.lower())
        self.assertNotIn("WhatsApp", response.answer)
        self.assertNotIn("familias", response.answer.lower())

    def test_elderly_population_max_question_uses_age_structure_metric_lookup(self) -> None:
        class _FailingPlanner:
            def plan(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("planner should not be called")

        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.tools = _FakePoliticalTools()
        agent.planner = _FailingPlanner()

        response = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Cuál es la sección con mayor número de personas mayores?",
                    municipality_id="29070",
                )
            )
        )

        self.assertIn("intent=elderly_population_max_section", response.methodology)
        self.assertIn("workflow=age_structure_metric_lookup", response.methodology)
        self.assertEqual(response.tools_used, ["get_age_structure"])
        self.assertIn("Sección 12 · Calahonda", response.answer)
        self.assertIn("1.120", response.answer)
        self.assertIn("personas mayores", response.answer)
        self.assertNotIn("promocion", response.answer.lower())
        self.assertNotIn("WhatsApp", response.answer)
        self.assertNotIn("campaña", response.answer.lower())

    def test_ambiguous_change_question_asks_clarification_not_generic_advice(self) -> None:
        class _FailingPlanner:
            def plan(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("planner should not be called")

        class _FailingWorkflowExecutor:
            def run(self, *_args, **_kwargs):  # pragma: no cover - must not be called
                raise AssertionError("workflow should not be called")

        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.planner = _FailingPlanner()
        agent.workflow_executor = _FailingWorkflowExecutor()

        response = asyncio.run(
            agent.chat(AnalystChatRequest(message="¿Qué secciones cambiaron más entre 2019 y 2023?", municipality_id="29070"))
        )

        self.assertIn("cambio demográfico", response.answer)
        self.assertIn("cambio electoral", response.answer)
        self.assertIn("cambio de renta", response.answer)
        self.assertIn("intent=ambiguous_change_between_years", response.methodology)
        self.assertEqual(response.tools_used, [])
        self.assertNotIn("Camino Campanales", response.answer)
        self.assertNotIn("Riviera Sur", response.answer)
        self.assertNotIn("decisión territorial general", response.answer.lower())
        self.assertNotIn("WhatsApp", response.answer)

    def test_change_question_with_active_population_layer_returns_population_change(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.tools = _FakePoliticalTools()

        response = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Qué secciones cambiaron más entre 2019 y 2023?",
                    municipality_id="29070",
                    context={"active_layer": "population"},
                )
            )
        )

        self.assertIn("intent=population_change_between_years", response.methodology)
        self.assertEqual(response.tools_used, ["get_population_change_ranking"])
        self.assertIn("cambio demográfico", response.answer)
        self.assertNotIn("decisión territorial general", response.answer.lower())

    def test_change_question_with_active_electoral_layer_returns_electoral_change(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.tools = _FakePoliticalTools()

        response = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Qué secciones cambiaron más entre 2019 y 2023?",
                    municipality_id="29070",
                    context={"active_layer": "electoral"},
                )
            )
        )

        self.assertIn("intent=electoral_change_between_years", response.methodology)
        self.assertEqual(response.tools_used, ["get_electoral_change_ranking"])
        self.assertIn("cambio electoral", response.answer)
        self.assertNotIn("decisión territorial general", response.answer.lower())

    def test_consultative_housing_conversation_asks_then_continues_context(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)
        conversation_id = "ctx-housing-dialogue"

        greeting = asyncio.run(agent.chat(AnalystChatRequest(message="Hola", municipality_id="29070", conversation_id=conversation_id)))
        housing = asyncio.run(agent.chat(AnalystChatRequest(message="Háblame de la vivienda", municipality_id="29070", conversation_id=conversation_id)))
        follow_up = asyncio.run(agent.chat(AnalystChatRequest(message="Para vivir, tengo niños pequeños", municipality_id="29070", conversation_id=conversation_id)))

        self.assertIn("Hola. Soy Ask soctrace", greeting.answer)
        self.assertEqual(greeting.tools_used, [])
        self.assertIn("vivir, invertir o potencial de revalorización", housing.answer)
        self.assertEqual(housing.tools_used, [])
        self.assertEqual(housing.tables, [])
        self.assertIn("niños pequeños", follow_up.answer)
        self.assertIn("colegios", follow_up.answer.lower())
        self.assertIn("población infantil", follow_up.answer)
        self.assertEqual(follow_up.tools_used, [])
        self.assertNotIn("curso", follow_up.answer.lower())
        self.assertNotIn("promocionar", follow_up.answer.lower())

    def test_consultative_training_conversation_keeps_socioeconomic_context(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)
        conversation_id = "ctx-training-dialogue"

        first = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="Quiero anunciar una formación para capacitar a personas en edad laboral.",
                    municipality_id="29070",
                    conversation_id=conversation_id,
                )
            )
        )
        follow_up = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Estás considerando Inteligencia Socioeconómica?",
                    municipality_id="29070",
                    conversation_id=conversation_id,
                )
            )
        )

        self.assertIn("Hipótesis de trabajo", first.answer)
        self.assertIn("Inteligencia Socioeconómica", first.answer)
        self.assertIn("Socioeconomic Intelligence", first.data_layers_used)
        self.assertNotIn("AMPAs", first.answer)
        self.assertNotIn("familias", first.answer.lower())
        self.assertIn("Sí", follow_up.answer)
        self.assertIn("Capas:", follow_up.answer)
        self.assertIn("productive_complexity_index", follow_up.answer)
        self.assertIn("Socioeconomic Intelligence", follow_up.data_layers_used)

    def test_consultative_analytical_followup_stays_metric_based(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        agent.tools = _FakePoliticalTools()
        conversation_id = "ctx-analytical-dialogue"

        first = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="Cuál es la sección con mayor población?",
                    municipality_id="29070",
                    conversation_id=conversation_id,
                )
            )
        )
        follow_up = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Y con más personas mayores?",
                    municipality_id="29070",
                    conversation_id=conversation_id,
                )
            )
        )

        self.assertIn("Sección 23 · Riviera Sur", first.answer)
        self.assertEqual(first.tools_used, ["get_population_ranking"])
        self.assertIn("personas mayores", follow_up.answer)
        self.assertEqual(follow_up.tools_used, ["get_age_structure"])
        self.assertNotIn("promocionar", follow_up.answer.lower())
        self.assertNotIn("Sí. Para una decisión territorial general", follow_up.answer)

    def test_consultative_sports_facilities_uses_facility_logic_not_promotion(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)

        response = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Qué secciones deberían contar con instalaciones deportivas?",
                    municipality_id="29070",
                )
            )
        )

        self.assertIn("instalaciones deportivas", response.answer)
        self.assertIn("población joven", response.answer)
        self.assertIn("densidad", response.answer)
        self.assertNotIn("WhatsApp", response.answer)
        self.assertNotIn("prueba gratuita", response.answer)
        self.assertNotIn("promocionar el", response.answer.lower())

    def test_general_territorial_composer_refuses_analytical_metric_question(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        tool_result = _FakePoliticalTools().get_population_density("29070")
        sections = agent._sections_from_rows(tool_result.rows)
        plan = PoliticalPlanner().plan("Quiero hacer una acción local en Mijas, ¿cómo lo enfocarías?", "29070")

        composed = compose_final_answer(
            message="¿Cuál es la sección con mayor población?",
            intent="general_territorial_advice",
            plan=plan,
            tool_result=tool_result,
            sections=sections,
        )

        self.assertIn("no define una priorización territorial general", composed.answer)
        self.assertNotIn("Sí. Para una decisión territorial general", composed.answer)
        self.assertIn("¿Quieres ver el ranking completo de secciones?", composed.follow_up_questions)
        self.assertNotIn("¿Quieres que lo convierta en un plan de promoción de 2 semanas?", composed.follow_up_questions)

    def test_capabilities_question_is_conversational(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )

        response = asyncio.run(
            agent.chat(AnalystChatRequest(message="¿Qué puedes hacer?", municipality_id="29070"))
        )

        self.assertIn("SocTrace Political Analyst", response.answer)
        self.assertIn("decisión política", response.answer)
        self.assertNotIn("backend", response.answer.lower())
        self.assertEqual(response.data_used, [])

    def test_broad_campaign_question_routes_to_campaign_plan_without_refusal(self) -> None:
        plan = PoliticalPlanner().plan("¿Podrías ayudarme a organizar una campaña electoral en Mijas?", "mijas")

        self.assertEqual(plan.goal, "campaign_plan")
        self.assertFalse(plan.needs_clarification)
        self.assertIsNone(plan.target_party)
        self.assertIn("get_turnout_analysis", plan.required_tools)
        self.assertIn("rank_sections_by_opportunity", plan.required_tools)

    def test_design_strategy_routes_to_campaign_plan(self) -> None:
        plan = PoliticalPlanner().plan("Diseña una estrategia electoral para Mijas", "29070")

        self.assertEqual(plan.goal, "campaign_plan")
        self.assertFalse(plan.needs_clarification)

    def test_candidate_visit_question_routes_to_visit_plan(self) -> None:
        plan = PoliticalPlanner().plan("¿Qué secciones debería visitar primero el candidato?", "29070")

        self.assertEqual(plan.goal, "candidate_visit_plan")

    def test_abstention_question_routes_to_abstention_analysis(self) -> None:
        plan = PoliticalPlanner().plan("¿Dónde es más alta la abstención?", "29070")

        self.assertEqual(plan.goal, "abstention_analysis")

    def test_party_growth_detects_pp(self) -> None:
        plan = PoliticalPlanner().plan("¿Dónde puede crecer el PP?", "29070")

        self.assertEqual(plan.goal, "party_growth_opportunity")
        self.assertEqual(plan.domain, "electoral_strategy")
        self.assertEqual(plan.target_party, "PP")

    def test_english_course_routes_to_territorial_marketing(self) -> None:
        question = "Voy a ofertar un curso de inglés gratuito para promocionarme, ¿en qué lugar de Mijas debería promocionarlo y cómo debería hacerlo?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertEqual(intelligence.conversation_type, "strategic")
        self.assertEqual(intelligence.user_intent, "territorial_marketing")
        self.assertEqual(intelligence.suggested_response_mode, "territorial_consultant")
        self.assertIn(plan.goal, {"territorial_marketing", "service_launch"})
        self.assertNotEqual(plan.domain, "electoral")
        self.assertIsNone(plan.target_party)
        self.assertEqual(plan.target_service, "free English course")
        self.assertIn("families", plan.target_audience)

    def test_english_course_workflow_uses_territorial_tools_not_election_results(self) -> None:
        question = "Voy a ofertar un curso de inglés gratuito para promocionarme, ¿en qué lugar de Mijas debería promocionarlo y cómo debería hacerlo?"
        tools = _FakePoliticalTools()
        plan = PoliticalPlanner().plan(question, "29070")
        output = PoliticalAnalystWorkflowExecutor(tools).run(plan, year=2023)

        self.assertTrue(output.tool_result.rows)
        self.assertNotIn("get_election_results", output.tool_names)
        self.assertIn("get_age_structure", output.tool_names)
        self.assertIn("get_population_density", output.tool_names)
        row = output.tool_result.rows[0]
        self.assertIn("target_audience_reason", row)
        self.assertIn("recommended_channel", row)
        self.assertIn("recommended_action", row)

    def test_english_course_response_is_territorial_consultant(self) -> None:
        question = "Voy a ofertar un curso de inglés gratuito para promocionarme, ¿en qué lugar de Mijas debería promocionarlo y cómo debería hacerlo?"
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan(question, "29070")
        output = PoliticalAnalystWorkflowExecutor(_FakePoliticalTools()).run(plan, year=2023)
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message=question,
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=output.tool_result,
                plan=plan,
                tool_names=output.tool_names,
            )
        )

        self.assertIn("curso", response.answer.lower())
        self.assertIn("familias", response.answer.lower())
        self.assertIn("Canales de comunicación", response.answer)
        self.assertIn("Cómo lo haría", response.answer)
        self.assertNotIn("filas internas suficientes", response.answer)
        self.assertNotIn("PP", response.answer)
        self.assertEqual(response.synthetic_variables_used, [])
        self.assertEqual(response.tables[0].title, "Prioridades territoriales")

    def test_sports_facilities_routes_to_public_facility_domain(self) -> None:
        question = "¿Qué secciones deberían contar con instalaciones deportivas?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertEqual(intelligence.conversation_type, "strategic")
        self.assertEqual(intelligence.user_intent, "public_facility_prioritization")
        self.assertEqual(plan.goal, "sports_facilities_planning")
        self.assertEqual(plan.domain, "sports_facilities_planning")
        self.assertIsNone(plan.target_party)

    def test_sports_facilities_response_is_not_course_promotion(self) -> None:
        question = "¿Qué secciones deberían contar con instalaciones deportivas?"
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan(question, "29070")
        output = PoliticalAnalystWorkflowExecutor(_FakePoliticalTools()).run(plan, year=2023)
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message=question,
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=output.tool_result,
                plan=plan,
                tool_names=output.tool_names,
            )
        )

        self.assertEqual(output.tool_result.name, "sports_facilities_planning_workflow")
        self.assertIn("instalaciones deportivas", response.answer)
        self.assertIn("población joven", response.answer)
        self.assertIn("densidad", response.answer)
        self.assertEqual(response.display_mode, "chat")
        self.assertEqual(response.tables[0].title, "Prioridades para instalaciones deportivas")
        self.assertNotIn("WhatsApp", response.answer)
        self.assertNotIn("prueba gratuita", response.answer)
        self.assertNotIn("AMPAs", response.answer)
        self.assertNotIn("promocionar el", response.answer.lower())
        self.assertNotIn("filas internas suficientes", response.answer)

    def test_real_estate_routes_to_housing_domain(self) -> None:
        question = "¿En qué zona de Mijas debería comprarme una vivienda?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertEqual(intelligence.conversation_type, "strategic")
        self.assertEqual(intelligence.user_intent, "housing_area_recommendation")
        self.assertEqual(plan.goal, "real_estate_location_advice")
        self.assertEqual(plan.domain, "real_estate_location_advice")
        self.assertIsNone(plan.target_party)

    def test_real_estate_response_is_not_course_promotion(self) -> None:
        question = "¿En qué zona de Mijas debería comprarme una vivienda?"
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan(question, "29070")
        output = PoliticalAnalystWorkflowExecutor(_FakePoliticalTools()).run(plan, year=2023)
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message=question,
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=output.tool_result,
                plan=plan,
                tool_names=output.tool_names,
            )
        )

        self.assertEqual(output.tool_result.name, "real_estate_location_advice_workflow")
        self.assertIn("comprar vivienda", response.answer)
        self.assertIn("vivir", response.answer)
        self.assertIn("revalorización", response.answer)
        self.assertEqual(response.display_mode, "chat")
        self.assertEqual(response.tables[0].title, "Zonas residenciales a analizar")
        self.assertNotIn("WhatsApp", response.answer)
        self.assertNotIn("prueba gratuita", response.answer)
        self.assertNotIn("curso", response.answer.lower())
        self.assertNotIn("promocionar", response.answer.lower())
        self.assertNotIn("filas internas suficientes", response.answer)

    def test_local_academy_routes_to_service_or_commercial_launch(self) -> None:
        question = "Voy a abrir una academia en Mijas, ¿qué zonas tienen mejor perfil?"
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertIn(plan.goal, {"service_launch", "territorial_marketing", "commercial_targeting"})
        self.assertIn(plan.domain, {"territorial_marketing", "territorial"})
        self.assertIsNone(plan.target_party)

    def test_public_outreach_routes_to_public_or_demographic_targeting(self) -> None:
        question = "Quiero lanzar una campaña municipal para informar a familias con hijos adolescentes. ¿Dónde debería empezar?"
        plan = PoliticalPlanner().plan(question, "29070")

        self.assertIn(plan.goal, {"public_service_outreach", "demographic_targeting"})
        self.assertIn(plan.domain, {"public_service", "demographic"})
        self.assertIsNone(plan.target_party)

    def test_unemployment_aid_outreach_is_public_service_not_course_promotion(self) -> None:
        question = "Tengo una noticia importante que dar sobre ayudas a personas desempleadas, ¿en qué zona del municipio debería concentrar la promoción?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        output = PoliticalAnalystWorkflowExecutor(_FakePoliticalTools()).run(plan, year=2023)
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message=question,
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=output.tool_result,
                plan=plan,
                tool_names=output.tool_names,
            )
        )

        self.assertEqual(intelligence.user_intent, "public_service_outreach")
        self.assertEqual(plan.goal, "public_service_outreach")
        self.assertEqual(plan.domain, "public_service")
        self.assertIn("Socioeconomic Intelligence", response.data_layers_used)
        self.assertEqual(response.display_mode, "chat")
        self.assertIn("comunicación pública", response.answer)
        self.assertIn("ayudas a personas desempleadas", response.answer)
        self.assertIn("servicios sociales", response.answer.lower())
        self.assertNotIn("prueba gratuita", response.answer)
        self.assertNotIn("reserva", response.answer.lower())
        self.assertNotIn("AMPAs", response.answer)
        self.assertNotIn("Instagram/TikTok", response.answer)
        self.assertNotIn("demanda educativa", " ".join(response.warnings + response.limitations).lower())

    def test_labor_training_uses_socioeconomic_intelligence(self) -> None:
        question = "Quiero anunciar una formación para capacitar a personas en edad laboral. ¿En qué secciones me recomiendas que intensifique la promoción de esta formación?"
        intelligence = ConversationIntelligenceLayer().classify(question)
        plan = PoliticalPlanner().plan(question, "29070")
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        output = PoliticalAnalystWorkflowExecutor(_FakePoliticalTools()).run(plan, year=2023)
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message=question,
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=output.tool_result,
                plan=plan,
                tool_names=output.tool_names,
            )
        )

        self.assertEqual(intelligence.user_intent, "labor_training_outreach")
        self.assertEqual(plan.goal, "labor_training_outreach")
        self.assertEqual(plan.domain, "public_service")
        self.assertEqual(output.tool_result.name, "labor_training_outreach_workflow")
        self.assertIn("rank_sections_for_labor_training_outreach", output.tool_names)
        self.assertIn("marts.socioeconomic_intelligence_signals", output.tool_result.data_used)
        self.assertIn("Socioeconomic Intelligence", response.data_layers_used)
        self.assertIn("personas en edad laboral", response.answer)
        self.assertIn("potencial productivo", response.answer)
        self.assertIn("empleabilidad", response.answer)
        self.assertNotIn("AMPAs", response.answer)
        self.assertNotIn("colegios", response.answer.lower())
        self.assertNotIn("prueba gratuita", response.answer)

    def test_follow_up_uses_previous_socioeconomic_context(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)
        conversation_id = "ctx-labor-training"
        first_question = "Quiero anunciar una formación para capacitar a personas en edad laboral. ¿En qué secciones me recomiendas que intensifique la promoción de esta formación?"
        first_response = asyncio.run(
            agent.chat(AnalystChatRequest(message=first_question, municipality_id="29070", conversation_id=conversation_id))
        )
        follow_up = asyncio.run(
            agent.chat(AnalystChatRequest(message="¿Estás considerando los datos de la capa Inteligencia Socioeconómica?", municipality_id="29070", conversation_id=conversation_id))
        )

        self.assertIn("Socioeconomic Intelligence", first_response.data_layers_used)
        self.assertEqual(follow_up.display_mode, "chat")
        self.assertEqual(follow_up.tables, [])
        self.assertIn("sí", follow_up.answer.lower())
        self.assertIn("Inteligencia Socioeconómica", follow_up.answer)
        self.assertIn("potencial productivo", follow_up.answer)
        self.assertNotIn("decisión territorial general", follow_up.answer)

    def test_follow_up_lists_variables_used_from_previous_recommendation(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)
        conversation_id = "ctx-vars"
        first_question = "Quiero anunciar una formación para capacitar a personas en edad laboral. ¿En qué secciones me recomiendas que intensifique la promoción de esta formación?"
        asyncio.run(agent.chat(AnalystChatRequest(message=first_question, municipality_id="29070", conversation_id=conversation_id)))
        follow_up = asyncio.run(
            agent.chat(AnalystChatRequest(message="¿Qué variables has usado para esa recomendación?", municipality_id="29070", conversation_id=conversation_id))
        )

        self.assertIn("Capas:", follow_up.answer)
        self.assertIn("Socioeconomic Intelligence", follow_up.answer)
        self.assertIn("productive_complexity_index", follow_up.answer)
        self.assertIn("Variables", follow_up.answer)

    def test_follow_up_provides_previous_recommendation_provenance(self) -> None:
        agent = PoliticalAnalystAgent(
            session=SimpleNamespace(),
            settings=SimpleNamespace(ask_analyst_enabled=True, llm_provider="mock", gemini_api_key=None),
        )
        tools = _FakePoliticalTools()
        agent.tools = tools
        agent.workflow_executor = PoliticalAnalystWorkflowExecutor(tools)
        conversation_id = "ctx-provenance"
        first_question = "Quiero anunciar una formación para capacitar a personas en edad laboral. ¿En qué secciones me recomiendas que intensifique la promoción de esta formación?"
        asyncio.run(agent.chat(AnalystChatRequest(message=first_question, municipality_id="29070", conversation_id=conversation_id)))

        follow_up = asyncio.run(
            agent.chat(
                AnalystChatRequest(
                    message="¿Qué herramientas y variables has usado para esa recomendación?",
                    municipality_id="29070",
                    conversation_id=conversation_id,
                )
            )
        )

        self.assertEqual(follow_up.display_mode, "chat")
        self.assertIn("Capas:", follow_up.answer)
        self.assertIn("Herramientas:", follow_up.answer)
        self.assertIn("rank_sections_for_labor_training_outreach", follow_up.answer)
        self.assertIn("productive_complexity_index", follow_up.answer)
        self.assertIn("Socioeconomic Intelligence", follow_up.data_layers_used)
        self.assertIn("rank_sections_for_labor_training_outreach", follow_up.tools_used)
        self.assertIn("productive_complexity_index", follow_up.variables_used)

    def test_generic_unknown_uses_general_territorial_not_election_results(self) -> None:
        question = "Quiero hacer una acción local en Mijas, ¿cómo lo enfocarías?"
        plan = PoliticalPlanner().plan(question, "29070")
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        output = agent._execute_plan(plan, question, "29070", 2023, AnalystChatRequest(message=question))

        self.assertEqual(plan.goal, "general_territorial_advice")
        self.assertNotEqual(plan.domain, "electoral")
        self.assertNotEqual(output.tool_result.name, "get_election_results")

    def test_campaign_workflow_uses_multiple_tools_and_keeps_evidence_table(self) -> None:
        tools = _FakePoliticalTools()
        plan = PoliticalPlanner().plan("¿Podrías ayudarme a organizar una campaña electoral en Mijas?", "mijas")
        output = PoliticalAnalystWorkflowExecutor(tools).run(plan, year=2023)

        self.assertGreaterEqual(len(set(output.tool_names)), 6)
        self.assertEqual(output.tool_result.name, "campaign_plan_workflow")
        self.assertTrue(output.tool_result.rows)
        evidence = output.tool_result.rows[0]
        self.assertIn("section_id", evidence)
        self.assertIn("population_total", evidence)
        self.assertIn("abstention_rate_pct", evidence)
        self.assertIn("strategic_label", evidence)

    def test_agent_campaign_response_sounds_consultative(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("Diseña una estrategia electoral para Mijas", "29070")
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message="Diseña una estrategia electoral para Mijas",
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=_FakePoliticalTools().build_campaign_recommendation("29070"),
                plan=plan,
                tool_names=["get_election_results", "get_turnout_analysis", "rank_sections_by_opportunity"],
            )
        )

        self.assertNotIn("No encuentro datos internos suficientes", response.answer)
        self.assertIn("Recomendación ejecutiva", response.answer)
        self.assertTrue(response.follow_up_questions)
        self.assertTrue(response.tables)
        self.assertTrue(response.executive_thesis)

    def test_composer_handles_budget_and_hides_backend_artifacts(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("¿Si tuviera que invertir 5000€ en una campaña electoral para PP cómo debería hacerlo?", "29070")
        tool_result = _FakePoliticalTools().build_campaign_recommendation("29070")
        sections = agent._sections_from_rows(tool_result.rows)

        composed = compose_final_answer(
            message="¿Si tuviera que invertir 5000€ en una campaña electoral para PP cómo debería hacerlo?",
            intent=plan.goal,
            plan=plan,
            tool_result=tool_result,
            sections=sections,
        )

        self.assertIn("5.000 euros", composed.answer)
        self.assertIn("1.500 euros", composed.answer)
        self.assertIn("Recomendación ejecutiva", composed.answer)
        self.assertIn("Qué no haría", composed.answer)
        self.assertNotIn("turnout_opportunity_score", composed.answer)
        self.assertNotIn("Residential Growth Area", composed.answer)
        self.assertLessEqual(len(composed.follow_up_questions), 3)
        self.assertEqual(composed.tables[0].columns[:5], ["Prioridad", "Seccion", "Por que importa", "Accion", "Objetivo"])

    def test_agent_budget_response_uses_final_composer(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("¿Si tuviera que invertir 5000€ en una campaña electoral para PP cómo debería hacerlo?", "29070")
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message="¿Si tuviera que invertir 5000€ en una campaña electoral para PP cómo debería hacerlo?",
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=_FakePoliticalTools().build_campaign_recommendation("29070"),
                plan=plan,
                tool_names=["get_election_results", "get_turnout_analysis", "rank_sections_by_opportunity"],
            )
        )

        self.assertIn("campana quirurgica", response.answer)
        self.assertIn("5.000 euros", response.answer)
        self.assertIn("PP", response.answer)
        self.assertIn("Qué no haría", response.answer)
        self.assertEqual(response.synthetic_variables_used, [])
        self.assertLessEqual(len(response.follow_up_questions), 3)
        self.assertEqual(response.tables[0].title, "Prioridades de campana")

    def test_candidate_visit_response_has_ranked_unique_sections(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("¿Qué secciones debería visitar primero el candidato?", "29070")
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message="¿Qué secciones debería visitar primero el candidato?",
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=_FakePoliticalTools().build_campaign_recommendation("29070"),
                plan=plan,
                tool_names=["rank_sections_by_opportunity"],
            )
        )

        section_names = [row[1] for row in response.tables[0].rows]
        self.assertEqual(len(section_names), len(set(section_names)))
        self.assertIn("priorizaria estas zonas", response.answer.lower())
        self.assertIn("reunion", response.answer.lower())

    def test_abstention_response_is_analytical_and_evidenced(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("¿Dónde es más alta la abstención?", "29070")
        response = asyncio.run(
            agent._build_response(
                intent=plan.goal,
                message="¿Dónde es más alta la abstención?",
                municipality_id="29070",
                conversation_id="test-conversation",
                tool_result=_FakePoliticalTools().build_campaign_recommendation("29070"),
                plan=plan,
                tool_names=["get_turnout_analysis"],
            )
        )

        self.assertTrue(response.answer.startswith("La abstención más alta"))
        self.assertIn("Evidencia", response.answer)
        self.assertIn("Metodología", response.answer)
        self.assertNotIn("campana quirurgica", response.answer)

    def test_executive_reasoning_outputs_decision_fields(self) -> None:
        agent = PoliticalAnalystAgent(session=SimpleNamespace(), settings=SimpleNamespace(llm_provider="mock", gemini_api_key=None))
        plan = PoliticalPlanner().plan("¿podrías ayudarme a organizar una campaña electoral en Mijas?", "29070")
        tool_result = _FakePoliticalTools().build_campaign_recommendation("29070")
        sections = agent._sections_from_rows(tool_result.rows)

        reasoning = ExecutiveReasoningLayer().reason(
            message="¿podrías ayudarme a organizar una campaña electoral en Mijas?",
            plan=plan,
            tool_result=tool_result,
            sections=sections,
        )

        self.assertTrue(reasoning.executive_thesis)
        self.assertTrue(reasoning.strategic_decision)
        self.assertTrue(reasoning.recommended_actions)
        self.assertTrue(reasoning.what_not_to_do)

    def test_grounding_guard_returns_structured_decision(self) -> None:
        result = _FakePoliticalTools().build_campaign_recommendation("29070")
        allowed = _is_grounded_synthesis("Yo priorizaría Sección 17 · Campo Mijas por la evidencia disponible.", result)
        rejected = _is_grounded_synthesis("Según una encuesta interna inventada, ganará otra sección 2907099999.", result)

        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.violations, [])
        self.assertFalse(rejected.allowed)
        self.assertTrue(rejected.violations)


class _FakePoliticalTools:
    rows = [
        {
            "section_id": "2907001017",
            "section_name": "Sección 17 · Campo Mijas",
            "population_total": 1300,
            "winning_party": "PP",
            "winning_party_pct": 34.9,
            "runner_up_pct": 28.1,
            "victory_margin_pct": 6.8,
            "target_party_vote_pct": 34.9,
            "abstention_rate_pct": 50.1,
            "population_growth_pct": 3.2,
            "average_age": 41.5,
            "under_30_pct": 31.0,
            "population_density": 1850,
            "individual_income": 14861,
            "pct_employed": 62.0,
            "pct_unemployed": 14.0,
            "pct_qualified_occupations": 31.0,
            "employment_norm": 58.0,
            "unemployment_norm": 72.0,
            "qualified_occupation_norm": 49.0,
            "low_education_norm": 64.0,
            "vulnerability_index": 68.0,
            "human_capital_index": 52.0,
            "resilience_index": 55.0,
            "productive_complexity_index": 61.0,
            "productive_complexity_label": "High",
            "labor_training_score": 72.4,
            "opportunity_score": 103.5,
        },
        {
            "section_id": "2907001020",
            "section_name": "Sección 20 · Las Lagunas",
            "population_total": 1600,
            "winning_party": "PSOE",
            "winning_party_pct": 31.2,
            "runner_up_pct": 30.2,
            "victory_margin_pct": 1.0,
            "target_party_vote_pct": 30.2,
            "abstention_rate_pct": 43.4,
            "population_growth_pct": 5.7,
            "average_age": 39.8,
            "under_30_pct": 34.5,
            "population_density": 2100,
            "individual_income": 15120,
            "pct_employed": 66.0,
            "pct_unemployed": 11.0,
            "pct_qualified_occupations": 36.0,
            "employment_norm": 67.0,
            "unemployment_norm": 55.0,
            "qualified_occupation_norm": 62.0,
            "low_education_norm": 48.0,
            "vulnerability_index": 57.0,
            "human_capital_index": 65.0,
            "resilience_index": 61.0,
            "productive_complexity_index": 74.0,
            "productive_complexity_label": "High",
            "labor_training_score": 78.8,
            "opportunity_score": 98.1,
        },
    ]

    def get_election_results(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_election_results", ["marts.mv_electoral_behavior"])

    def get_turnout_analysis(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_turnout_analysis", ["marts.mv_electoral_behavior"])

    def get_population_trend(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_population_trend", ["marts.v_population_layer"])

    def get_population_ranking(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_population_ranking",
            rows=[
                {
                    "section_id": "2907001023",
                    "section_name": "Sección 23 · Riviera Sur",
                    "year": 2025,
                    "population_total": 5351,
                    "population_density": 2450.5,
                }
            ],
            data_used=["marts.v_population_layer", "marts.dim_seccion_display"],
            methodology="Fake population ranking.",
            warnings=[],
        )

    def get_elderly_population_ranking(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_age_structure",
            rows=[
                {
                    "section_id": "2907001012",
                    "section_name": "Sección 12 · Calahonda",
                    "year": 2025,
                    "population_total": 3500,
                    "over_65_pct": 32.0,
                    "elderly_population": 1120,
                }
            ],
            data_used=["marts.v_population_layer", "marts.v_mapa_age_structure_2023", "marts.dim_seccion_display"],
            methodology="Fake elderly population ranking.",
            warnings=[],
        )

    def get_population_change_ranking(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_population_change_ranking",
            rows=[
                {
                    "section_id": "2907001023",
                    "section_name": "Sección 23 · Riviera Sur",
                    "population_start": 4100,
                    "population_end": 5351,
                    "population_change": 1251,
                    "population_change_pct": 30.51,
                }
            ],
            data_used=["marts.v_population_layer", "marts.dim_seccion_display"],
            methodology="Fake population change ranking.",
            warnings=[],
        )

    def get_electoral_change_ranking(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_electoral_change_ranking",
            rows=[
                {
                    "section_id": "2907001017",
                    "section_name": "Sección 17 · Campo Mijas",
                    "turnout_start": 48.0,
                    "turnout_end": 56.5,
                    "turnout_change_pct": 8.5,
                    "abstention_change_pct": -8.5,
                    "winning_party_start": "PSOE",
                    "winning_party_end": "PP",
                    "winning_party_change_pct": 6.0,
                }
            ],
            data_used=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            methodology="Fake electoral change ranking.",
            warnings=[],
        )

    def get_income_change_ranking(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_income_change_ranking",
            rows=[
                {
                    "section_id": "2907001020",
                    "section_name": "Sección 20 · Las Lagunas",
                    "individual_income_start": 14100,
                    "individual_income_end": 15800,
                    "individual_income_change": 1700,
                    "individual_income_change_pct": 12.06,
                }
            ],
            data_used=["marts.v_income_level_layer", "marts.dim_seccion_display"],
            methodology="Fake income change ranking.",
            warnings=[],
        )

    def get_population_density(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_population_density", ["marts.v_population_layer"])

    def get_age_structure(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_age_structure", ["marts.v_mapa_age_structure_2023"])

    def get_family_youth_profile(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_family_youth_profile", ["marts.v_mapa_age_structure_2023"])

    def get_income_profile(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_income_profile", ["marts.v_income_level_layer"])

    def get_socioeconomic_profile(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_socioeconomic_profile", ["marts.v_income_level_layer"])

    def get_socioeconomic_intelligence_profile(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_socioeconomic_intelligence_profile", ["marts.socioeconomic_intelligence_signals"])

    def rank_sections_for_labor_training_outreach(self, *args, **kwargs) -> AnalystToolResult:
        rows = [dict(row) for row in self.rows]
        rows.sort(key=lambda item: item.get("labor_training_score") or 0, reverse=True)
        return AnalystToolResult(
            name="rank_sections_for_labor_training_outreach",
            rows=rows,
            data_used=[
                "marts.socioeconomic_intelligence_signals",
                "marts.v_population_layer",
                "marts.v_mapa_age_structure_2023",
                "marts.v_income_level_layer",
            ],
            methodology="Fake labor training ranking.",
            warnings=[],
        )

    def get_land_built_profile(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("get_land_built_profile", ["marts.v_land_built_environment"])

    def get_foreign_population_profile(self, *args, **kwargs) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_foreign_population_profile",
            rows=[],
            data_used=[],
            methodology="No foreign population fixture.",
            warnings=[],
        )

    def rank_sections_by_opportunity(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("rank_sections_by_opportunity", ["marts.mv_electoral_behavior", "marts.v_population_layer"])

    def build_campaign_recommendation(self, *args, **kwargs) -> AnalystToolResult:
        return self._result("build_campaign_recommendation", ["marts.mv_electoral_behavior", "marts.v_income_level_layer"])

    def _result(self, name: str, data_used: list[str]) -> AnalystToolResult:
        return AnalystToolResult(
            name=name,
            rows=[dict(row) for row in self.rows],
            data_used=data_used,
            methodology=f"{name} fake methodology.",
            warnings=[],
        )


class PoliticalAnalystSchemaTest(unittest.TestCase):
    def test_normalizes_mijas_municipality_alias(self) -> None:
        payload = AnalystChatRequest(message="Where can PP grow?", municipality_id="mijas")

        self.assertEqual(payload.municipality_id, "29070")

    def test_accepts_numeric_municipality_id(self) -> None:
        payload = AnalystChatRequest(message="Where can PP grow?", municipality_id="29070")

        self.assertEqual(payload.municipality_id, "29070")

    def test_normalizes_empty_optional_context_strings(self) -> None:
        payload = AnalystChatRequest(
            message="¿Cuál es la sección electoral más poblada de Mijas?",
            municipality_id="29070",
            context={
                "active_layer": "",
                "active_year": 2025,
                "selected_section_id": "",
                "selected_election": "",
            },
        )

        self.assertIsNone(payload.context.active_layer)
        self.assertIsNone(payload.context.selected_section_id)
        self.assertIsNone(payload.context.selected_election)

    def test_accepts_null_selected_section_id(self) -> None:
        payload = AnalystChatRequest(
            message="¿Cuál es la sección electoral más poblada de Mijas?",
            municipality_id="29070",
            context={"selected_section_id": None},
        )

        self.assertIsNone(payload.context.selected_section_id)


class _StubPoliticalAnalystAgent:
    def __init__(self) -> None:
        self.payloads: list[AnalystChatRequest] = []

    async def chat(self, payload: AnalystChatRequest) -> AnalystChatResponse:
        self.payloads.append(payload)
        return AnalystChatResponse(
            answer="Analyst agent invoked.",
            methodology="Stubbed route validation test.",
            confidence="high",
            data_used=["marts.v_population_layer"],
            conversation_id=payload.conversation_id,
        )


class PoliticalAnalystRouteValidationTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_political_analyst_agent, None)

    def test_chat_route_accepts_empty_selected_section_id(self) -> None:
        stub = _StubPoliticalAnalystAgent()
        app.dependency_overrides[get_political_analyst_agent] = lambda: stub

        response = TestClient(app).post(
            "/api/v1/analyst/chat",
            json={
                "message": "¿Cuál es la sección electoral más poblada de Mijas?",
                "conversation_id": "test-conversation",
                "municipality_id": "29070",
                "context": {
                    "active_layer": "population",
                    "active_year": 2025,
                    "selected_section_id": "",
                    "selected_election": None,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stub.payloads[0].context.selected_section_id, None)
        self.assertEqual(stub.payloads[0].municipality_id, "29070")

    def test_chat_route_accepts_mijas_alias_and_null_selected_section_id(self) -> None:
        stub = _StubPoliticalAnalystAgent()
        app.dependency_overrides[get_political_analyst_agent] = lambda: stub

        response = TestClient(app).post(
            "/api/v1/analyst/chat",
            json={
                "message": "¿Cuál es la sección electoral más poblada de Mijas?",
                "conversation_id": "test-conversation",
                "municipality_id": "mijas",
                "context": {
                    "active_layer": "population",
                    "active_year": 2025,
                    "selected_section_id": None,
                    "selected_election": None,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stub.payloads[0].context.selected_section_id, None)
        self.assertEqual(stub.payloads[0].municipality_id, "29070")

    def test_chat_route_forwards_minimum_analytical_queries_once_without_rewriting(self) -> None:
        questions = [
            "¿Qué sección tiene mayor densidad en 2025?",
            "¿Cuál fue el partido ganador en la sección 18?",
            "Compara la renta de las secciones 10 y 23.",
            "¿Dónde obtuvo el PP su mejor resultado en 2023?",
        ]

        for index, question in enumerate(questions):
            stub = _StubPoliticalAnalystAgent()
            app.dependency_overrides[get_political_analyst_agent] = lambda: stub
            response = TestClient(app).post(
                "/api/v1/analyst/chat",
                json={
                    "message": question,
                    "conversation_id": f"legacy-route-{index}",
                    "municipality_id": "29070",
                    "context": {"active_year": 2025, "selected_section_id": None},
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(stub.payloads), 1)
            self.assertEqual(stub.payloads[0].message, question)
            self.assertEqual(stub.payloads[0].conversation_id, f"legacy-route-{index}")

    def test_chat_route_rejects_empty_message_with_422(self) -> None:
        stub = _StubPoliticalAnalystAgent()
        app.dependency_overrides[get_political_analyst_agent] = lambda: stub

        response = TestClient(app).post(
            "/api/v1/analyst/chat",
            json={"message": "", "context": {"selected_section_id": None}},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(stub.payloads, [])

    def test_chat_route_preserves_agent_exception_as_server_error(self) -> None:
        class _FailingAgent:
            async def chat(self, payload: AnalystChatRequest) -> AnalystChatResponse:
                raise RuntimeError("controlled-agent-failure")

        app.dependency_overrides[get_political_analyst_agent] = _FailingAgent
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/analyst/chat",
            json={"message": "Consulta", "conversation_id": "failing-agent"},
        )

        self.assertEqual(response.status_code, 500)


if __name__ == "__main__":
    unittest.main()
