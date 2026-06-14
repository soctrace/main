from __future__ import annotations

import unittest

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class ChainedQueriesTest(unittest.TestCase):
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

    def test_party_dominates_youngest_section_runs_chained_analysis(self):
        response = self.ask("¿Qué partido domina la sección más joven?", "youngest-party")

        self.assertEqual(response.data["tool"], "chained_youngest_section_party_dominance")
        self.assertIn("La sección más joven es", response.answer)
        self.assertIn("partido con mayor fortaleza media", response.answer)
        self.assertTrue(response.data["rows"])

    def test_age_cohort_projection_for_2027(self):
        response = self.ask("¿Cuántas personas tendrán 18 años en 2027?", "cohort-2027")

        self.assertEqual(response.data["tool"], "age_cohort_projection")
        self.assertIn("18 años", response.answer)
        self.assertIn("2027", response.answer)
        self.assertIn("nuevos votantes", response.answer)
        self.assertTrue(response.data["rows"])

    def test_first_time_voter_sections_for_2027(self):
        response = self.ask("¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027?", "cohort-sections-2027")

        self.assertEqual(response.data["tool"], "age_cohort_projection")
        self.assertIn("Resultados principales", response.answer)
        self.assertTrue(response.entities)


if __name__ == "__main__":
    unittest.main()
