import unittest

from app.ask.answer_guard import AnswerGuard
from app.ask.rendering.answer_guard import RenderAnswerGuard
from app.ask.tools_v2.schemas import ToolResult


def ranking_result() -> ToolResult:
    return ToolResult(
        tool_name="rank_sections",
        operation="rank_sections",
        status="ok",
        rows=[
            {"section_name": "Sección 23 · Riviera Sur", "value": 5351, "year": 2025, "value_label": "habitantes"}
        ],
        metadata={"year": 2025},
    )


class RenderAnswerGuardTest(unittest.TestCase):
    def setUp(self):
        self.guard = RenderAnswerGuard()

    def test_accepts_grounded_answer(self):
        result = self.guard.validate(
            question="¿Cuál es la sección con mayor población?",
            answer="La sección con mayor población es Sección 23 · Riviera Sur, con 5.351 habitantes en 2025.",
            tool_result=ranking_result(),
        )
        self.assertTrue(result.ok, result.reasons)

    def test_rejects_sql_and_internal_tables(self):
        result = self.guard.validate(
            question="Pregunta",
            answer="SELECT * FROM marts.agent_section_profile",
            tool_result=ranking_result(),
        )
        self.assertFalse(result.ok)

    def test_rejects_wrong_top_section(self):
        result = self.guard.validate(
            question="Pregunta",
            answer="La sección con mayor población es Sección 99, con 5.351 habitantes en 2025.",
            tool_result=ranking_result(),
        )
        self.assertFalse(result.ok)

    def test_rejects_wrong_value(self):
        result = self.guard.validate(
            question="Pregunta",
            answer="La sección destacada es Sección 23 · Riviera Sur, con 9999 habitantes en 2025.",
            tool_result=ranking_result(),
        )
        self.assertFalse(result.ok)

    def test_rejects_missing_entity_list_items(self):
        tool_result = ToolResult(
            tool_name="persistent_winner",
            operation="persistent_winner",
            status="ok",
            rows=[
                {"section_name": "Sección 1", "value": 100.0},
                {"section_name": "Sección 2", "value": 100.0},
            ],
            metadata={"party": "PP"},
        )
        result = self.guard.validate(
            question="¿Dónde gana siempre el PP?",
            answer="El PP gana siempre en Sección 1.",
            tool_result=tool_result,
        )
        self.assertFalse(result.ok)

    def test_rejects_demographic_only_age_group_voting_answer(self):
        result = self.guard.validate(
            question="¿Qué suelen votar las personas mayores de 45 años?",
            answer="La sección destacada es Sección 23 · Riviera Sur, con 912 personas mayores de 65.",
            tool_result=ToolResult(
                tool_name="rank_sections",
                operation="rank_sections",
                status="ok",
                rows=[
                    {"section_name": "Sección 23 · Riviera Sur", "value": 912, "value_label": "Poblacion mayor de 65"}
                ],
            ),
        )
        self.assertFalse(result.ok)

    def test_requires_caveat_for_ecological_age_vote_answer(self):
        tool_result = ToolResult(
            tool_name="ecological_vote_profile_by_age_group",
            operation="ecological_vote_profile_by_age_group",
            status="ok",
            rows=[{"party": "PP", "weighted_vote_pct": 35.2, "value": 35.2}],
        )
        rejected = self.guard.validate(
            question="¿Qué suelen votar los jóvenes?",
            answer="El partido más asociado territorialmente es PP.",
            tool_result=tool_result,
        )
        self.assertFalse(rejected.ok)

        accepted = self.guard.validate(
            question="¿Qué suelen votar los jóvenes?",
            answer="No es voto individual por edad; es una estimación territorial. PP aparece como mayor asociación.",
            tool_result=tool_result,
        )
        self.assertTrue(accepted.ok, accepted.reasons)


class ToolAnswerGuardTest(unittest.TestCase):
    def setUp(self):
        self.guard = AnswerGuard()

    def test_rejects_rank_sections_for_age_group_voting_question(self):
        result = self.guard.validate_tool_result(
            question="¿Qué suelen votar las personas mayores de 45 años?",
            tool_name="rank_sections",
            tool_args={"metric": "population_over_65"},
            tool_result=ranking_result(),
        )
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
