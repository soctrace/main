from __future__ import annotations

import unittest

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class ConversationalCorrectionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = SessionLocal()
        cls.settings = get_settings()
        cls.settings.ask_use_llm_planner = False
        cls.service = AskSocTraceService(cls.session, cls.settings)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.close()

    def ask(self, question: str, conversation_id: str):
        return self.service.ask(
            AskRequest(
                question=question,
                activeMunicipality="29070",
                conversationId=conversation_id,
                mode="debug",
            )
        )

    def test_initial_percentage_question_uses_relative_metric(self):
        response = self.ask("¿En qué sección viven mayor porcentaje de personas mayores de 65 años?", "relative-initial")

        self.assertEqual(response.data["tool"], "rank_sections")
        self.assertEqual(response.data["metadata"]["metric"], "population_over_65_pct")
        self.assertIn("porcentaje", response.answer.lower())
        self.assertIn("%", response.answer)

    def test_followup_correction_switches_absolute_to_percentage(self):
        first = self.ask("¿Dónde viven más personas mayores de 65 años?", "relative-followup")
        second = self.ask("Ese es el número absoluto, me refiero al porcentaje", "relative-followup")

        self.assertEqual(first.data["metadata"]["metric"], "population_over_65")
        self.assertEqual(second.data["metadata"]["metric"], "population_over_65_pct")
        self.assertIn("Tienes razón", second.answer)
        self.assertIn("%", second.answer)

    def test_relative_phrasings_are_understood(self):
        for index, wording in enumerate(("en porcentaje", "valor relativo", "no absoluto"), start=1):
            self.ask("¿Dónde viven más personas mayores de 65 años?", f"relative-wording-{index}")
            response = self.ask(f"Lo quiero ver {wording}", f"relative-wording-{index}")

            self.assertEqual(response.data["metadata"]["metric"], "population_over_65_pct")
            self.assertIn("%", response.answer)


if __name__ == "__main__":
    unittest.main()
