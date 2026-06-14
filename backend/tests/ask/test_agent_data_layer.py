import unittest

import yaml
from sqlalchemy import text

from app.core.database import SessionLocal


REQUIRED_VIEWS = [
    "marts.agent_section_lookup",
    "marts.agent_population_age",
    "marts.agent_section_profile",
    "marts.agent_electoral_results",
    "marts.agent_electoral_summary",
    "marts.agent_income_sources",
    "marts.agent_housing_profile",
]

REQUIRED_COLUMNS = {
    "marts.agent_section_lookup": ["municipio_id", "municipio_nombre", "section_id", "section_number", "section_name", "display_name"],
    "marts.agent_population_age": ["municipio_id", "municipio_nombre", "section_id", "section_name", "year", "gender", "age_cohort", "age_min", "age_max", "people"],
    "marts.agent_section_profile": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "year",
        "population_total",
        "average_age",
        "population_over_65",
        "income_individual",
        "abstention_pct",
        "winner_party",
    ],
    "marts.agent_electoral_results": ["municipio_id", "section_id", "election_id", "canonical_party", "votes", "valid_votes", "vote_pct"],
    "marts.agent_electoral_summary": ["municipio_id", "section_id", "election_id", "abstention_pct", "winner_party", "second_party", "margin_pct"],
    "marts.agent_income_sources": ["municipio_id", "section_id", "year", "income_individual", "income_household", "pension_share"],
    "marts.agent_housing_profile": ["municipio_id", "section_id", "year", "market_price_estimated_m2", "residential_pressure_index"],
}


class AgentDataLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = SessionLocal()
        try:
            cls.session.execute(text("SELECT 1 FROM marts.agent_section_profile LIMIT 1")).first()
        except Exception as exc:  # pragma: no cover - only used when local DB is absent
            raise unittest.SkipTest(f"Agent data layer is not installed in the local database: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.close()

    def scalar(self, sql: str):
        return self.session.execute(text(sql)).scalar()

    def test_required_agent_views_exist(self) -> None:
        for relation in REQUIRED_VIEWS:
            schema, table = relation.split(".")
            with self.subTest(relation=relation):
                exists = self.scalar(
                    f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.views
                        WHERE table_schema = '{schema}'
                          AND table_name = '{table}'
                    )
                    """
                )
                self.assertTrue(exists)

    def test_required_columns_exist(self) -> None:
        for relation, columns in REQUIRED_COLUMNS.items():
            schema, table = relation.split(".")
            found = {
                row[0]
                for row in self.session.execute(
                    text(
                        f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = '{schema}'
                          AND table_name = '{table}'
                        """
                    )
                ).all()
            }
            for column in columns:
                with self.subTest(relation=relation, column=column):
                    self.assertIn(column, found)

    def test_views_return_mijas_rows(self) -> None:
        for relation in REQUIRED_VIEWS:
            with self.subTest(relation=relation):
                count = self.scalar(f"SELECT COUNT(*) FROM {relation} WHERE municipio_id = '29070'")
                self.assertGreater(count, 0)

    def test_section_lookup_has_current_mijas_sections(self) -> None:
        count = self.scalar("SELECT COUNT(DISTINCT section_id) FROM marts.agent_section_lookup WHERE municipio_id = '29070'")
        self.assertEqual(count, 37)

    def test_key_section_profile_metrics_are_usable(self) -> None:
        metrics = ["population_total", "average_age", "population_over_65", "abstention_pct", "winner_party"]
        for metric in metrics:
            with self.subTest(metric=metric):
                count = self.scalar(
                    f"SELECT COUNT(*) FROM marts.agent_section_profile WHERE municipio_id = '29070' AND {metric} IS NOT NULL"
                )
                self.assertGreater(count, 0)

    def test_domain_metrics_are_usable(self) -> None:
        cases = [
            ("marts.agent_electoral_results", "vote_pct"),
            ("marts.agent_electoral_summary", "abstention_pct"),
            ("marts.agent_income_sources", "income_individual"),
            ("marts.agent_housing_profile", "market_price_estimated_m2"),
            ("marts.agent_housing_profile", "residential_pressure_index"),
        ]
        for relation, metric in cases:
            with self.subTest(relation=relation, metric=metric):
                count = self.scalar(f"SELECT COUNT(*) FROM {relation} WHERE municipio_id = '29070' AND {metric} IS NOT NULL")
                self.assertGreater(count, 0)

    def test_population_and_domain_years_exist(self) -> None:
        self.assertGreaterEqual(self.scalar("SELECT COUNT(DISTINCT year) FROM marts.agent_section_profile WHERE municipio_id = '29070'"), 1)
        self.assertGreaterEqual(self.scalar("SELECT COUNT(DISTINCT election_id) FROM marts.agent_electoral_summary WHERE municipio_id = '29070'"), 1)
        self.assertGreaterEqual(self.scalar("SELECT COUNT(DISTINCT year) FROM marts.agent_income_sources WHERE municipio_id = '29070'"), 1)
        self.assertGreaterEqual(self.scalar("SELECT COUNT(DISTINCT year) FROM marts.agent_housing_profile WHERE municipio_id = '29070'"), 1)

    def test_semantic_catalog_metrics_use_existing_agent_views(self) -> None:
        with open("app/ask/semantic_catalog.yaml", encoding="utf-8") as catalog_file:
            catalog = yaml.safe_load(catalog_file)
        metrics = catalog.get("metrics", {})
        self.assertTrue(metrics)
        for metric_id, definition in metrics.items():
            relation = definition.get("view")
            with self.subTest(metric=metric_id, relation=relation):
                self.assertIsNotNone(relation)
                self.assertNotIn(".ask_", relation)
                schema, table = relation.split(".")
                exists = self.scalar(
                    f"""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.views
                        WHERE table_schema = '{schema}'
                          AND table_name = '{table}'
                    )
                    """
                )
                self.assertTrue(exists)


if __name__ == "__main__":
    unittest.main()
