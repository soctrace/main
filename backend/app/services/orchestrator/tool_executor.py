from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql import QueryExecutor, SqlGenerator, SqlValidator
from app.ask.tools_v2 import ToolContext, ToolExecutorV2, ToolRegistryV2, ToolResult
from app.services.orchestrator.tool_registry import OrchestratorToolRegistry


DATA_LAYER_BY_PUBLIC_TOOL = {
    "get_population_profile": "Population Intelligence",
    "get_age_structure": "Age Structure",
    "get_income_profile": "Income Intelligence",
    "get_socioeconomic_profile": "Socioeconomic Intelligence",
    "get_electoral_results": "Electoral Intelligence",
    "get_housing_profile": "Housing Intelligence",
    "get_urban_profile": "Urban Intelligence",
    "lookup_section_by_address": "Section Lookup",
    "rank_sections": "Territorial Ranking",
    "compare_sections": "Section Profile",
    "compare_years": "Population Intelligence",
    "cross_metric_analysis": "Cross-domain Intelligence",
}


SOURCE_BY_PUBLIC_TOOL = {
    "get_population_profile": "marts.agent_section_profile",
    "get_age_structure": "marts.agent_section_profile",
    "get_income_profile": "marts.agent_income_sources",
    "get_socioeconomic_profile": "marts.agent_section_profile",
    "get_electoral_results": "marts.agent_electoral_results",
    "get_housing_profile": "marts.agent_housing_profile",
    "get_urban_profile": "marts.agent_housing_profile",
    "lookup_section_by_address": "marts.agent_section_lookup",
    "rank_sections": "approved semantic catalog",
    "compare_sections": "marts.agent_section_profile",
    "compare_years": "marts.agent_population_growth",
    "cross_metric_analysis": "approved semantic catalog",
}


class SafeDataToolExecutor:
    def __init__(self, session: Session):
        self.public_registry = OrchestratorToolRegistry()
        self.semantic_catalog = SemanticCatalog()
        self.sql_generator = SqlGenerator()
        self.sql_validator = SqlValidator(self.sql_generator.approved_relations)
        self.query_executor = QueryExecutor(session)
        self.registry_v2 = ToolRegistryV2(self.query_executor, self.sql_validator, self.semantic_catalog)
        self.executor_v2 = ToolExecutorV2(self.registry_v2)

    async def execute(self, tool_name: str, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        if not self.public_registry.has_tool(tool_name):
            return ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="unsupported",
                methodology_plain="La herramienta solicitada no está aprobada para el Orchestrator.",
                caveats=["El LLM solo puede llamar tools registradas en el catálogo seguro."],
                error_code="tool_not_allowed",
                error_message="Tool not allowed by orchestrator registry.",
            )

        if tool_name == "lookup_section_by_address":
            metadata = self.public_registry.metadata_for(tool_name)
            return ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="unsupported",
                methodology_plain="No se ha ejecutado geocodificación porque SocTrace aún no tiene una herramienta fiable de lookup por dirección en el catálogo seguro.",
                caveats=list(metadata.limitations if metadata else []),
                sources=list(metadata.source_views if metadata else []),
                metadata={
                    "ok": False,
                    "data_layer": metadata.data_layer if metadata else DATA_LAYER_BY_PUBLIC_TOOL.get(tool_name),
                    "variables_used": ["address", "section_id"],
                    "source_view": SOURCE_BY_PUBLIC_TOOL.get(tool_name),
                    "limitations": list(metadata.limitations if metadata else []),
                },
                error_code="address_lookup_unavailable",
                error_message="Todavía no tengo una herramienta fiable para geocodificar esa calle dentro de SocTrace.",
            )

        if tool_name == "compare_sections" and len(arguments.get("sections") or []) > 1:
            combined_rows = []
            sources: list[str] = []
            caveats: list[str] = []
            for section in arguments["sections"][:8]:
                result = await self.executor_v2.execute("section_profile", {
                    "municipio_id": arguments.get("municipio_id") or context.municipio_id,
                    "section": section,
                    "year": arguments.get("year"),
                    "include_domains": arguments.get("include_domains") or ["population", "income", "electoral", "housing"],
                }, context)
                combined_rows.extend(result.rows)
                sources.extend(result.sources)
                caveats.extend(result.caveats)
            metadata = self.public_registry.metadata_for(tool_name)
            return ToolResult(
                tool_name=tool_name, operation="compare_sections",
                status="ok" if combined_rows else "empty", rows=combined_rows,
                sources=list(dict.fromkeys(sources)), caveats=list(dict.fromkeys(caveats)),
                methodology_plain="Comparación determinista de las secciones retenidas en el contexto conversacional.",
                metadata={"ok": bool(combined_rows), "data_layer": metadata.data_layer if metadata else "Section Profile",
                          "variables_used": arguments.get("include_domains") or [], "source_view": "marts.agent_section_profile",
                          "limitations": list(dict.fromkeys(caveats))},
            )

        internal_name, internal_args = self._map_to_internal_tool(tool_name, arguments)
        result = await self.executor_v2.execute(internal_name, internal_args, context)
        result.tool_name = tool_name
        metadata = self.public_registry.metadata_for(tool_name)
        variables_used = self._variables_used(tool_name, arguments) or list(metadata.variables_available if metadata else [])
        result.metadata.update(
            {
                "ok": result.status == "ok",
                "internal_tool_name": internal_name,
                "data_layer": metadata.data_layer if metadata else DATA_LAYER_BY_PUBLIC_TOOL.get(tool_name),
                "variables_used": variables_used,
                "source_view": (metadata.source_views[0] if metadata and metadata.source_views else SOURCE_BY_PUBLIC_TOOL.get(tool_name)),
                "limitations": list(result.caveats or metadata.limitations if metadata else result.caveats),
            }
        )
        if metadata and not result.sources:
            result.sources = list(metadata.source_views)
        elif SOURCE_BY_PUBLIC_TOOL.get(tool_name) and not result.sources:
            result.sources = [SOURCE_BY_PUBLIC_TOOL[tool_name]]
        return result

    def _map_to_internal_tool(self, tool_name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        args = dict(arguments)
        municipio_id = args.get("municipio_id") or "29070"
        year = args.get("year")
        limit = args.get("limit") or 5
        section = args.get("section")

        if tool_name == "get_population_profile":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year, "include_domains": ["population"]}
            return "rank_sections", {"municipio_id": municipio_id, "metric": "population_total", "order": "desc", "year": year, "limit": limit}
        if tool_name == "get_age_structure":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year, "include_domains": ["population"]}
            metric = args.get("metric") or "population_under_30"
            return "rank_sections", {"municipio_id": municipio_id, "metric": metric, "order": args.get("order") or "desc", "year": year, "limit": limit}
        if tool_name == "get_income_profile":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year, "include_domains": ["income"]}
            return "rank_sections", {"municipio_id": municipio_id, "metric": "income_individual", "order": args.get("order") or "desc", "year": year, "limit": limit}
        if tool_name == "get_housing_profile":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year, "include_domains": ["housing"]}
            return "rank_sections", {"municipio_id": municipio_id, "metric": "market_price_estimated_m2", "order": args.get("order") or "desc", "year": year, "limit": limit}
        if tool_name == "get_urban_profile":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year, "include_domains": ["housing"]}
            return "rank_sections", {"municipio_id": municipio_id, "metric": "building_intensity", "order": args.get("order") or "desc", "year": year, "limit": limit}
        if tool_name == "get_socioeconomic_profile":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "year": year}
            return "rank_sections", {"municipio_id": municipio_id, "metric": "income_individual", "order": "desc", "year": year, "limit": limit}
        if tool_name == "get_electoral_results":
            if section:
                return "section_profile", {"municipio_id": municipio_id, "section": section, "include_domains": ["electoral"]}
            party = args.get("party")
            intent = args.get("intent") or "results"
            if intent == "growth_opportunity" and party:
                return "electoral_growth_opportunity", {
                    "municipio_id": municipio_id,
                    "party": party,
                    "election_type": args.get("election_type") or "MUNICIPALES",
                    "election_year": args.get("election_year"),
                    "limit": limit,
                }
            if party:
                return "party_strength", {
                    "municipio_id": municipio_id,
                    "party": party,
                    "election_type": args.get("election_type"),
                    "election_year": args.get("election_year"),
                    "limit": limit,
                }
            return "rank_sections", {
                "municipio_id": municipio_id,
                "metric": "abstention_pct",
                "order": "desc",
                "election_type": args.get("election_type"),
                "election_year": args.get("election_year"),
                "limit": limit,
            }
        if tool_name == "rank_sections":
            return "rank_sections", args
        if tool_name == "compare_sections":
            first_section = (args.get("sections") or [None])[0]
            return "section_profile", {
                "municipio_id": municipio_id,
                "section": first_section,
                "year": year,
                "include_domains": args.get("include_domains") or ["population", "income", "electoral", "housing"],
            }
        if tool_name == "compare_years":
            return "population_growth", {
                "municipio_id": municipio_id,
                "start_year": args["start_year"],
                "end_year": args["end_year"],
                "rank_by": "growth_pct",
                "order": args.get("order") or "desc",
                "limit": limit,
            }
        if tool_name == "cross_metric_analysis":
            return "cross_metric_ranking", {
                "municipio_id": municipio_id,
                "year": year,
                "metrics": args.get("metrics") or [],
                "limit": limit,
            }
        return tool_name, args

    def _variables_used(self, tool_name: str, arguments: dict[str, Any]) -> list[str]:
        if tool_name == "rank_sections":
            return [str(arguments.get("metric"))] if arguments.get("metric") else []
        if tool_name == "get_population_profile":
            return ["population_total"]
        if tool_name == "get_age_structure":
            return [str(arguments.get("metric") or "population_under_30")]
        if tool_name == "get_income_profile":
            return ["income_individual"]
        if tool_name == "get_housing_profile":
            return ["market_price_estimated_m2"]
        if tool_name == "get_urban_profile":
            return ["building_intensity"]
        if tool_name == "get_electoral_results":
            if arguments.get("intent") == "growth_opportunity":
                return [
                    "vote_pct",
                    "abstention_pct",
                    "margin_to_first_place",
                    "historical_recovery_room_pct",
                    "volatility_pct",
                    "electoral_growth_opportunity",
                ]
            return ["vote_pct", "abstention_pct", "winner_party"]
        if tool_name == "get_socioeconomic_profile":
            return ["income_individual", "population_total", "abstention_pct"]
        if tool_name == "compare_years":
            return ["population_absolute_change", "population_growth_pct"]
        if tool_name == "cross_metric_analysis":
            return [str(item.get("metric")) for item in arguments.get("metrics", []) if item.get("metric")]
        return []
