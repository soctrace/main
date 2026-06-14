from __future__ import annotations

import unittest

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class ElectoralSwitchingTest(unittest.TestCase):
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

    def test_most_disputed_sections_use_margin(self):
        response = self.ask("¿Cuáles son las secciones más disputadas?", "disputed")

        self.assertEqual(response.data["tool"], "rank_sections")
        self.assertEqual(response.data["metadata"]["metric"], "margin_pct")
        self.assertIn("margen", response.answer.lower())
        self.assertIn("frente a", response.answer)

    def test_participation_decline(self):
        response = self.ask("¿Qué zonas han reducido más la participación?", "participation-decline")

        self.assertEqual(response.data["tool"], "participation_decline")
        self.assertIn("2019", response.answer)
        self.assertIn("2023", response.answer)
        self.assertTrue(response.data["rows"])

    def test_winner_switch_by_election_type(self):
        response = self.ask("¿Qué secciones cambian de partido ganador según la elección?", "winner-switch")

        self.assertEqual(response.data["tool"], "winner_switch_by_election_type")
        self.assertIn("partidos ganadores distintos", response.answer)
        self.assertTrue(response.data["rows"])

    def test_abstention_increase_risk_proxy(self):
        response = self.ask("¿Qué secciones podrían aumentar la abstención?", "abstention-risk")

        self.assertEqual(response.data["tool"], "abstention_increase_risk")
        self.assertIn("No es una predicción estadística cerrada", response.answer)
        self.assertTrue(response.data["rows"])


if __name__ == "__main__":
    unittest.main()
