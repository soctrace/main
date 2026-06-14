import unittest

from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql import SqlValidator
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolRegistryV2
from tests.ask.test_tools_v2 import FakeQueryExecutor


class EmptyQueryExecutor(FakeQueryExecutor):
    def execute(self, sql: str):
        self.sql.append(sql)
        return []


class ToolsV2ExecutionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.query_executor = FakeQueryExecutor()
        self.registry = ToolRegistryV2(
            self.query_executor,
            SqlValidator(self.catalog.approved_relations),
            self.catalog,
        )
        self.executor = ToolExecutorV2(self.registry)
        self.context = ToolContext(municipio_id="29070", municipio_nombre="Mijas")

    async def execute_ok(self, tool_name: str, arguments: dict):
        result = await self.executor.execute(tool_name, arguments, self.context)
        self.assertEqual(result.status, "ok", result)
        self.assertTrue(result.rows)
        self.assertEqual(result.metadata["municipio_id"], "29070")
        self.assertFalse(any("marts.ask_" in sql for sql in self.query_executor.sql))
        return result

    async def test_rank_sections_population_total(self):
        result = await self.execute_ok("rank_sections", {"metric": "population_total", "limit": 5})
        self.assertEqual(result.chart_spec["type"], "bar")

    async def test_rank_sections_average_age_asc(self):
        result = await self.execute_ok("rank_sections", {"metric": "average_age", "order": "asc", "limit": 5})
        self.assertEqual(result.metadata["metric"], "average_age")

    async def test_rank_sections_population_over_65(self):
        result = await self.execute_ok("rank_sections", {"metric": "population_over_65", "limit": 5})
        self.assertEqual(result.rows[0]["value_label"], "Poblacion mayor de 65")

    async def test_aggregate_municipality_population_total(self):
        result = await self.execute_ok("aggregate_municipality", {"metric": "population_total"})
        self.assertEqual(result.chart_spec["type"], "metric")

    async def test_compare_years_average_age_largest_decrease(self):
        result = await self.execute_ok("compare_years", {"metric": "average_age", "direction": "largest_decrease"})
        self.assertIn("delta_abs", result.rows[0])

    async def test_population_growth_with_section_25_37_lineage(self):
        result = await self.execute_ok("population_growth", {"rank_by": "growth_abs"})
        self.assertIn("Sección 37", result.rows[0]["current_sections"])
        self.assertTrue(result.rows[0]["includes_split"])

    async def test_filter_sections_population_total_threshold(self):
        result = await self.execute_ok(
            "filter_sections",
            {"conditions": [{"metric": "population_total", "operator": ">", "value": 5000}]},
        )
        self.assertGreater(result.rows[0]["value"], 5000)

    async def test_section_profile_riviera_sur(self):
        result = await self.execute_ok("section_profile", {"section": "Riviera Sur"})
        self.assertIn("Riviera Sur", result.rows[0]["section_name"])

    async def test_party_strength_pp(self):
        result = await self.execute_ok("party_strength", {"party": "PP"})
        self.assertEqual(result.metadata["party"], "PP")

    async def test_persistent_winner_pp(self):
        result = await self.execute_ok("persistent_winner", {"party": "PP"})
        self.assertTrue(result.rows[0]["always_wins"])

    async def test_historical_party_average_riviera_sur(self):
        result = await self.execute_ok("historical_party_average", {"section": "Riviera Sur"})
        self.assertEqual(result.rows[0]["party"], "PP")

    async def test_age_cohort_projection_18_in_2027(self):
        result = await self.execute_ok(
            "age_cohort_projection",
            {"source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18},
        )
        self.assertEqual(result.rows[0]["target_age"], 18)

    async def test_age_cohort_projection_65_plus(self):
        result = await self.execute_ok("age_cohort_projection", {"min_age": 65, "max_age": 120})
        self.assertGreater(result.rows[0]["value"], 0)

    async def test_ecological_vote_profile_by_age_group(self):
        result = await self.execute_ok("ecological_vote_profile_by_age_group", {"min_age": 45})
        self.assertEqual(result.rows[0]["party"], "PP")
        self.assertEqual(result.chart_spec["x"], "party")
        self.assertEqual(result.chart_spec["y"], "weighted_vote_pct")
        self.assertIn("estimación territorial", result.caveats[0])

    async def test_electoral_viability_estimate(self):
        result = await self.execute_ok("electoral_viability_estimate", {"party": "PP"})
        self.assertEqual(result.metadata["estimate_type"], "electoral_viability")
        self.assertEqual(result.rows[0]["party"], "PP")
        self.assertIn("viability_index", result.rows[0])

    async def test_electoral_growth_opportunity(self):
        result = await self.execute_ok("electoral_growth_opportunity", {"party": "PP"})
        self.assertEqual(result.metadata["analysis_type"], "electoral_growth_opportunity")
        self.assertEqual(result.rows[0]["party"], "PP")
        self.assertIn("growth_score", result.rows[0])

    async def test_cross_metric_ranking_low_income_high_abstention(self):
        result = await self.execute_ok(
            "cross_metric_ranking",
            {
                "metrics": [
                    {"metric": "income_individual", "direction": "low", "weight": 0.5},
                    {"metric": "abstention_pct", "direction": "high", "weight": 0.5},
                ]
            },
        )
        self.assertIn("Es un índice territorial compuesto", result.caveats[0])
        self.assertIn("component_1", result.rows[0])

    async def test_correlation_analysis_income_vs_abstention(self):
        result = await self.execute_ok("correlation_analysis", {"x_metric": "income_individual", "y_metric": "abstention_pct"})
        self.assertEqual(result.chart_spec["x"], "x_value")
        self.assertEqual(result.chart_spec["y"], "y_value")

    async def test_empty_state(self):
        registry = ToolRegistryV2(EmptyQueryExecutor(), SqlValidator(self.catalog.approved_relations), self.catalog)
        result = await ToolExecutorV2(registry).execute("rank_sections", {"metric": "population_total"}, self.context)
        self.assertEqual(result.status, "empty")
        self.assertEqual(result.summary["row_count"], 0)

    async def test_invalid_tool_name(self):
        result = await self.executor.execute("not_a_tool", {}, self.context)
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.error_code, "unknown_tool")

    async def test_invalid_arguments(self):
        result = await self.executor.execute("rank_sections", {"order": "desc"}, self.context)
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.error_code, "invalid_tool_arguments")

    async def test_pending_tool_rejected(self):
        self.registry.tools["rank_sections"].status = "pending"
        result = await self.executor.execute("rank_sections", {"metric": "population_total"}, self.context)
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.error_code, "pending_tool")

    async def test_sql_validation_failure_converted_to_error(self):
        registry = ToolRegistryV2(FakeQueryExecutor(), SqlValidator(set()), self.catalog)
        result = await ToolExecutorV2(registry).execute("rank_sections", {"metric": "population_total"}, self.context)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error_code, "sql_validation_failed")
        self.assertNotIn("marts.", result.error_message or "")


if __name__ == "__main__":
    unittest.main()
