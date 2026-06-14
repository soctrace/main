import unittest

from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql import SqlValidator
from app.ask.tools_v2 import ToolRegistryV2


class FakeQueryExecutor:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, sql: str):
        self.sql.append(sql)
        if "latest_municipal_vote_pct" in sql and "viability" not in sql:
            return [
                {
                    "party": "PP",
                    "municipio_id": "29070",
                    "municipio_nombre": "Mijas",
                    "latest_municipal_year": 2023,
                    "latest_municipal_vote_pct": 35.4,
                    "latest_municipal_position": 1,
                    "sections_won": 14,
                    "sections_total": 31,
                    "average_historical_vote_pct": 31.2,
                    "trend_direction": "ascendente",
                    "trend_delta": 4.1,
                    "margin_vs_main_opponent": 3.6,
                    "competitive_sections": 9,
                    "territorial_strength_score": 45.16,
                    "average_gap_to_section_winner": 2.4,
                    "average_abstention_pct": 36.1,
                    "value": 35.4,
                },
                {
                    "party": "PSOE",
                    "municipio_id": "29070",
                    "municipio_nombre": "Mijas",
                    "latest_municipal_year": 2023,
                    "latest_municipal_vote_pct": 30.2,
                    "latest_municipal_position": 2,
                    "sections_won": 11,
                    "sections_total": 31,
                    "average_historical_vote_pct": 32.8,
                    "trend_direction": "estable",
                    "trend_delta": -0.4,
                    "margin_vs_main_opponent": -3.6,
                    "competitive_sections": 9,
                    "territorial_strength_score": 35.48,
                    "average_gap_to_section_winner": 4.5,
                    "average_abstention_pct": 36.1,
                    "value": 30.2,
                },
            ]
        if "growth_score" in sql and "opportunity_explanation" in sql:
            return [
                {
                    "section_id": "2907001011",
                    "section_name": "Sección 11 · Las Lagunas Norte",
                    "municipio_id": "29070",
                    "municipio_nombre": "Mijas",
                    "election_year": 2023,
                    "party": "PP",
                    "vote_pct": 31.2,
                    "winner_party": "PSOE",
                    "winner_vote_pct": 34.8,
                    "margin_to_first_place": 3.6,
                    "historical_vote_pct": 29.4,
                    "historical_best_vote_pct": 36.1,
                    "abstention_pct": 38.5,
                    "volatility_pct": 9.2,
                    "historical_recovery_room_pct": 4.9,
                    "growth_score": 82.3,
                    "opportunity_explanation": "sección competitiva: pequeña mejora puede cambiar la posición",
                    "value": 82.3,
                }
            ]
        if "target_strength_pct" in sql and "estimated_abstainers" in sql and "abstention_component" in sql:
            return [
                {
                    "section_id": "2907001007",
                    "section_name": "Sección 07 · Cala de Mijas",
                    "municipio_id": "29070",
                    "municipio_nombre": "Mijas",
                    "election_year": 2023,
                    "abstention_pct": 41.2,
                    "participation_pct": 58.8,
                    "margin_pct": 2.7,
                    "winner_party": "PSOE",
                    "census": 2100,
                    "population_total": 2500,
                    "target_strength_pct": 33.4,
                    "estimated_abstainers": 865,
                    "score": 0.82,
                    "interpretation": "oportunidad muy alta de movilización territorial",
                    "value": 0.82,
                },
                {
                    "section_id": "2907001020",
                    "section_name": "Sección 20 · Parque Andalucía",
                    "municipio_id": "29070",
                    "municipio_nombre": "Mijas",
                    "election_year": 2023,
                    "abstention_pct": 38.4,
                    "participation_pct": 61.6,
                    "margin_pct": 4.2,
                    "winner_party": "PP",
                    "census": 1900,
                    "population_total": 2300,
                    "target_strength_pct": 30.1,
                    "estimated_abstainers": 730,
                    "score": 0.74,
                    "interpretation": "oportunidad alta de movilización territorial",
                    "value": 0.74,
                },
            ]
        if "weighted_vote_pct" in sql and "age_group_population" in sql:
            return [
                {"party": "PP", "municipio_id": "29070", "municipio_nombre": "Mijas", "election_year": 2023, "min_age": 45, "max_age": 120, "weighted_vote_pct": 35.2, "average_vote_pct_in_high_age_sections": 37.1, "correlation_with_age_group_share": 0.31, "top_sections": "Sección 23 · Riviera Sur (54.2%)", "value": 35.2},
                {"party": "PSOE", "municipio_id": "29070", "municipio_nombre": "Mijas", "election_year": 2023, "min_age": 45, "max_age": 120, "weighted_vote_pct": 28.4, "average_vote_pct_in_high_age_sections": 27.0, "correlation_with_age_group_share": -0.12, "top_sections": "Sección 23 · Riviera Sur (54.2%)", "value": 28.4},
                {"party": "VOX", "municipio_id": "29070", "municipio_nombre": "Mijas", "election_year": 2023, "min_age": 45, "max_age": 120, "weighted_vote_pct": 12.1, "average_vote_pct_in_high_age_sections": 13.2, "correlation_with_age_group_share": 0.08, "top_sections": "Sección 23 · Riviera Sur (54.2%)", "value": 12.1},
            ]
        if "CORR(" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_nombre": "Mijas", "x_value": 25000, "y_value": 34.2, "correlation": -0.42}
            ]
        if "lineage_group_name" in sql:
            return [
                {"section_id": "29070_25_LINEAGE", "section_name": "Zona historica Seccion 25 / Maria Zambrano", "lineage_group_name": "Zona historica Seccion 25 / Maria Zambrano", "municipio_nombre": "Mijas", "start_year": 2021, "end_year": 2025, "population_start": 1000, "population_end": 1400, "growth_abs": 400, "growth_pct": 40.0, "includes_split": True, "current_sections": "Sección 25 + Sección 37"}
            ]
        if "elections_checked" in sql and "party_wins" in sql:
            return [
                {"section_id": "2907001004", "section_name": "Sección 04 · Centro Salud", "elections_checked": 12, "party_wins": 12, "value": 100.0, "always_wins": True, "elections_included": "Municipales 2019, Municipales 2023"}
            ]
        if "AVG(vote_pct)" in sql or "SUM(votes)" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "party": "PP", "value": 31.4, "elections_included": 4, "first_year": 2011, "last_year": 2023}
            ]
        if "source_age_band_population" in sql or "age_min <=" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2023, "source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18, "value": 120, "municipality_total": 900}
            ]
        if "component_1" in sql and "component_2" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_nombre": "Mijas", "value_1": 18000, "value_2": 42.0, "component_1": 0.9, "component_2": 0.8, "value": 0.85}
            ]
        if "municipal_average" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "value": 5200, "municipal_average": 2100}
            ]
        if "winner_party" in sql or "participation_pct" in sql or "abstention_pct" in sql or "market_price_estimated_m2" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2023, "value": 42.5}
            ]
        if "population_total" in sql and "SUM" in sql and "GROUP BY municipio_id" in sql:
            return [{"municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "value": 93000}]
        if "end_value - start_value" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_nombre": "Mijas", "start_year": 2021, "end_year": 2025, "start_value": 1000, "end_value": 1400, "delta_abs": 400, "delta_pct": 40.0, "value": 400}
            ]
        if "agent_section_lookup" in sql:
            return [
                {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "population_total": 5200, "average_age": 36.5, "income_individual": 22000, "winner_party": "PP", "market_price_estimated_m2": 2400}
            ]
        return [
            {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "value": 5200}
        ]


class ToolsV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.executor = FakeQueryExecutor()
        self.registry = ToolRegistryV2(self.executor, SqlValidator(self.catalog.approved_relations), self.catalog)

    def run_tool(self, name: str, args: dict):
        tool = self.registry.get(name)
        self.assertIsNotNone(tool)
        result = tool.execute(tool.input_schema.model_validate(args))
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.rows)
        self.assertFalse(any("marts.ask_" in sql for sql in self.executor.sql))
        return result

    def test_openai_schemas_are_exportable(self) -> None:
        for schema in self.registry.openai_schemas():
            self.assertIn("name", schema)
            self.assertIn("description", schema)
            self.assertIn("parameters", schema)

    def test_rank_sections_supported_metrics(self) -> None:
        cases = [
            ("population_total", "desc"),
            ("average_age", "asc"),
            ("population_over_65", "desc"),
            ("income_individual", "desc"),
            ("abstention_pct", "desc"),
            ("market_price_estimated_m2", "desc"),
        ]
        for metric, order in cases:
            with self.subTest(metric=metric):
                result = self.run_tool("rank_sections", {"metric": metric, "order": order, "limit": 5})
                self.assertEqual(result.operation, "rank_sections")

    def test_aggregate_municipality(self) -> None:
        for metric in ["population_total", "population_over_65", "population_under_30"]:
            with self.subTest(metric=metric):
                result = self.run_tool("aggregate_municipality", {"metric": metric})
                self.assertEqual(result.chart_spec["type"], "metric")

    def test_compare_years(self) -> None:
        cases = [
            {"metric": "population_total"},
            {"metric": "average_age", "direction": "largest_decrease"},
            {"metric": "average_age", "direction": "largest_increase"},
        ]
        for args in cases:
            with self.subTest(args=args):
                self.run_tool("compare_years", args)

    def test_population_growth_uses_lineage(self) -> None:
        result = self.run_tool("population_growth", {"rank_by": "growth_abs"})
        self.assertIn("Sección 37", result.rows[0]["current_sections"])
        self.assertTrue(result.rows[0]["includes_split"])

    def test_filter_sections(self) -> None:
        self.run_tool("filter_sections", {"conditions": [{"metric": "population_total", "operator": ">", "value": 5000}]})
        self.run_tool("filter_sections", {"conditions": [{"metric": "abstention_pct", "operator": "above_municipal_average"}]})

    def test_section_profile_resolution_inputs(self) -> None:
        for section in ["Riviera Sur", "section 23", "2907001023"]:
            with self.subTest(section=section):
                result = self.run_tool("section_profile", {"section": section})
                self.assertEqual(result.rows[0]["section_name"], "Sección 23 · Riviera Sur")

    def test_party_strength(self) -> None:
        self.run_tool("party_strength", {"party": "PP"})
        self.run_tool("party_strength", {"party": "PSOE", "historical": True})
        self.run_tool("party_strength", {"party": "VOX"})

    def test_persistent_winner(self) -> None:
        self.run_tool("persistent_winner", {"party": "PP"})
        self.run_tool("persistent_winner", {"party": "PSOE"})

    def test_historical_party_average(self) -> None:
        self.run_tool("historical_party_average", {"section": "Riviera Sur"})
        self.run_tool("historical_party_average", {"party": "PP"})

    def test_age_cohort_projection(self) -> None:
        self.run_tool("age_cohort_projection", {"source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18})
        self.run_tool("age_cohort_projection", {"source_year": 2023, "min_age": 18, "max_age": 22})
        self.run_tool("age_cohort_projection", {"min_age": 65, "max_age": 120, "group_by": "section"})

    def test_ecological_vote_profile_by_age_group(self) -> None:
        result = self.run_tool("ecological_vote_profile_by_age_group", {"min_age": 45})
        self.assertEqual(result.rows[0]["party"], "PP")
        self.assertEqual(result.chart_spec["type"], "bar")
        self.assertEqual(result.chart_spec["x"], "party")
        self.assertEqual(result.chart_spec["y"], "weighted_vote_pct")
        self.assertIn("voto individual por edad", result.caveats[0])
        self.assertTrue(any("marts.agent_population_age" in sql for sql in self.executor.sql))
        self.assertTrue(any("marts.agent_electoral_results" in sql for sql in self.executor.sql))

    def test_cross_metric_ranking(self) -> None:
        self.run_tool("cross_metric_ranking", {"metrics": [{"metric": "income_individual", "direction": "low", "weight": 0.5}, {"metric": "abstention_pct", "direction": "high", "weight": 0.5}]})
        self.run_tool("cross_metric_ranking", {"metrics": [{"metric": "population_under_30", "direction": "high", "weight": 0.5}, {"metric": "income_individual", "direction": "low", "weight": 0.5}]})

    def test_correlation_analysis(self) -> None:
        self.run_tool("correlation_analysis", {"x_metric": "income_individual", "y_metric": "abstention_pct"})
        self.run_tool("correlation_analysis", {"x_metric": "average_age", "y_metric": "participation_pct"})

    def test_electoral_viability_estimate(self) -> None:
        result = self.run_tool("electoral_viability_estimate", {"party": "PP"})
        self.assertEqual(result.metadata["estimate_type"], "electoral_viability")
        self.assertTrue(result.metadata["derived_estimate"])
        self.assertEqual(result.rows[0]["party"], "PP")
        self.assertIn(result.rows[0]["viability_label"], {"alta", "media-alta", "media", "media-baja", "baja"})
        self.assertIn("No es una probabilidad estadística real", result.caveats[0])

    def test_electoral_growth_opportunity(self) -> None:
        result = self.run_tool("electoral_growth_opportunity", {"party": "PP"})
        self.assertEqual(result.metadata["analysis_type"], "electoral_growth_opportunity")
        self.assertEqual(result.metadata["party"], "PP")
        self.assertEqual(result.rows[0]["section_name"], "Sección 11 · Las Lagunas Norte")
        self.assertIn("growth_score", result.rows[0])


if __name__ == "__main__":
    unittest.main()
