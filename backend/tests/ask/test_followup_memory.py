import unittest

from sqlalchemy import text

from app.ask.conversation import conversation_store
from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class AskFollowUpMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = SessionLocal()
        try:
            cls.session.execute(text("SELECT 1 FROM marts.ask_population_profile LIMIT 1")).first()
        except Exception as exc:  # pragma: no cover - only used when local DB is absent
            raise unittest.SkipTest(f"Local test database is not ready: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.close()

    def setUp(self) -> None:
        self.session.rollback()
        conversation_store.clear()
        self.service = AskSocTraceService(self.session, get_settings())

    def tearDown(self) -> None:
        self.session.rollback()

    def ask(self, question: str, conversation_id: str = "followup-test"):
        return self.service.ask(
            AskRequest(question=question, conversationId=conversation_id, activeMunicipality="29070")
        )

    def test_young_population_followup_confirms_year(self) -> None:
        first = self.ask("¿Qué secciones concentran más población joven?")
        self.assertIn("población joven", first.answer.lower() + str(first.table).lower())
        self.assertIsNotNone(first.session_memory)
        assert first.session_memory is not None
        self.assertEqual(first.session_memory["last_answer_context"]["metric"], "population_under_30")

        second = self.ask("¿Son datos de 2025?")
        self.assertIn("Sí", second.answer)
        self.assertIn("2025", second.answer)
        self.assertEqual(second.data, {"fromPreviousContext": True})
        self.assertNotIn("catálogo", second.answer.lower())

    def test_population_extreme_followup_returns_year_used(self) -> None:
        self.ask("¿Cuál es la sección con mayor población?", conversation_id="year-used")
        response = self.ask("¿De qué año son los datos?", conversation_id="year-used")
        self.assertIn("Son datos de", response.answer)
        self.assertRegex(response.answer, r"20\d{2}")
        self.assertEqual(response.data, {"fromPreviousContext": True})

    def test_growth_followup_returns_compared_period(self) -> None:
        self.ask("¿Qué zonas han crecido más?", conversation_id="period-used")
        response = self.ask("¿Qué periodo has comparado?", conversation_id="period-used")
        self.assertIn("2021", response.answer)
        self.assertIn("2025", response.answer)
        self.assertEqual(response.data, {"fromPreviousContext": True})

    def test_persistent_winner_followup_counts_previous_rows(self) -> None:
        relation = self.session.execute(text("SELECT to_regclass('marts.ask_electoral_summary')")).scalar()
        if relation is None:
            self.skipTest("marts.ask_electoral_summary is not available in this local database")
        self.ask("¿Dónde gana siempre el PP?", conversation_id="count-previous")
        response = self.ask("¿Cuántas son?", conversation_id="count-previous")
        self.assertRegex(response.answer, r"\d+")
        self.assertIn("secciones", response.answer)
        self.assertEqual(response.data, {"fromPreviousContext": True})

    def test_followup_change_year_reruns_previous_metric(self) -> None:
        self.ask("¿Cuál es la sección más joven?", conversation_id="change-year")
        response = self.ask("¿Y en 2023?", conversation_id="change-year")
        self.assertIn("2023", response.answer + str(response.table) + str(response.data))
        self.assertNotEqual(response.data, {"fromPreviousContext": True})
        self.assertIsNotNone(response.session_memory)
        assert response.session_memory is not None
        self.assertEqual(response.session_memory["last_answer_context"]["year"], 2023)


if __name__ == "__main__":
    unittest.main()
