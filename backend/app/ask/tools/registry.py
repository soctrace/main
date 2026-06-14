from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.analyst_repository import AnalystRepository
from app.services.local_analyst_service import DHondtCalculator, normalize


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class AskTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def openai_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }


class ToolRegistry:
    def __init__(self, tools: list[AskTool]):
        self._tools = {tool.name: tool for tool in tools}

    @property
    def tools(self) -> list[AskTool]:
        return list(self._tools.values())

    def openai_tools(self) -> list[dict[str, Any]]:
        return [tool.openai_definition() for tool in self.tools]

    def names(self) -> list[str]:
        return list(self._tools)

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {
                "ok": False,
                "error": f"No existe una herramienta aprobada llamada {name}.",
            }
        try:
            return {"ok": True, "result": tool.handler(arguments)}
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }


def _object_schema(
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _municipality_id(value: str | None) -> str:
    normalized = normalize(value or "29070")
    if normalized in {"mijas", "29070"}:
        return "29070"
    return value or "29070"


def _normalize_party(value: str | None) -> str:
    text = normalize(value or "")
    if "partido popular" in text or text == "pp":
        return "PP"
    if "socialista" in text or "psoe" in text:
        return "PSOE"
    if "vox" in text:
        return "VOX"
    if "ciudadanos" in text or text == "cs":
        return "CS"
    if "por mi pueblo" in text or text == "pmp":
        return "POR MI PUEBLO"
    return (value or "").upper()


def _format_number(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "no disponible"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _election_label(row: dict[str, Any]) -> str:
    label = f"{row['election_type']} {row['election_year']}"
    if row.get("election_month"):
        label += f"/{row['election_month']}"
    return label


def _resolve_section(repository: AnalystRepository, municipality_id: str, section: str) -> dict[str, Any] | None:
    hint = normalize(section)
    sections = repository.get_section_lookup(municipality_id)
    if hint.isdigit():
        requested_number = str(int(hint)).zfill(2)
        return next(
            (
                item
                for item in sections
                if str(item.get("section_number") or "").zfill(2) == requested_number
                or str(item["section_id"]).endswith(requested_number)
            ),
            None,
        )
    if hint.startswith("29070"):
        return next((item for item in sections if str(item["section_id"]) == hint), None)

    tokens = [token for token in hint.split() if len(token) > 1 and token not in {"la", "el", "de", "del", "seccion"}]
    best_match: tuple[int, dict[str, Any]] | None = None
    for item in sections:
        blob = normalize(
            " ".join(
                str(value)
                for value in (
                    item.get("display_name"),
                    item.get("nombre_barrio"),
                    item.get("zona_macro"),
                    item.get("section_number"),
                    item.get("section_id"),
                )
                if value
            )
        )
        score = 100 if hint in blob else sum(1 for token in tokens if token in blob)
        if score and (best_match is None or score > best_match[0]):
            best_match = (score, item)
    return best_match[1] if best_match else None


def build_tool_registry(session: Session) -> ToolRegistry:
    repository = AnalystRepository(session)

    def demographics_age_range(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        min_age = int(arguments["minAge"])
        max_age = int(arguments["maxAge"])
        gender = arguments.get("gender") or "all"
        group_by = arguments.get("groupBy") or "municipality"
        result = repository.get_demographics_age_range(
            municipality,
            int(arguments["year"]),
            min_age,
            max_age,
            gender=gender,
            group_by=group_by,
        )
        data = {
            "total": result["total"],
            "method": result["method"],
            "year": int(arguments["year"]),
            "ageRange": f"{min_age}-{max_age}",
            "municipality": municipality,
        }
        if group_by == "section":
            data["bySection"] = result["rows"]
        elif group_by == "gender":
            data["byGender"] = result["rows"]
        return data

    def age_cohort_abstention_by_section(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality") or "Mijas")
        year = int(arguments.get("year") or 2023)
        election_type = str(arguments.get("electionType") or "municipales").lower()
        min_age = int(arguments.get("minAge") or 18)
        max_age = int(arguments["maxAge"]) if arguments.get("maxAge") is not None else None
        effective_max_age = max_age if max_age is not None else 120
        sort_direction = str(arguments.get("sortDirection") or "desc").lower()
        result = repository.get_age_cohort_abstention_by_section(
            municipality,
            year,
            election_type,
            min_age,
            effective_max_age,
            sort_direction=sort_direction,
        )
        age_label = f"{min_age} años o más" if max_age is None else f"{min_age} a {max_age} años"
        return {
            "municipality": municipality,
            "year": year,
            "electionType": election_type,
            "ageRange": {
                "minAge": min_age,
                "maxAge": max_age,
                "label": age_label,
            },
            "method": "estimated_from_section_abstention_rate",
            "rows": [
                {
                    "sectionId": row["section_id"],
                    "sectionName": row["section_name"],
                    "ageRangePopulation": int(row["age_range_population"]),
                    "abstentionRatePct": float(row["abstention_rate_pct"]),
                    "estimatedAbstainers": int(row["estimated_abstainers"]),
                    "estimatedVoters": int(row["estimated_voters"]),
                    "totalElectoralCensus": int(row["total_electoral_census"]),
                    "totalVotes": int(row["total_votes"]),
                }
                for row in result["rows"]
            ],
            "totals": result["totals"],
            "caveats": [
                f"Este cálculo es una estimación ecológica. No sabemos el voto real individual por edad. Aplicamos la tasa de abstención total de cada sección a la población residente de {age_label} en esa sección.",
                "La poblacion por edad se estima proporcionalmente cuando el rango solicitado corta cohortes quinquenales.",
            ],
            "sources": ["core.poblacion_edad", "marts.mv_electoral_behavior", "marts.dim_seccion_display"],
        }

    def elections_party_section_history(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        party = _normalize_party(arguments.get("party"))
        section = _resolve_section(repository, municipality, str(arguments["section"]))
        if section is None:
            return {
                "found": False,
                "missing": "No se ha podido resolver la seccion solicitada.",
                "party": party,
            }
        rows = repository.get_normalized_election_results(
            municipality,
            party=party,
            section_id=str(section["section_id"]),
        )
        direction = arguments.get("direction") or "trend"
        sorted_rows = sorted(rows, key=lambda row: float(row["vote_pct"]))
        selected = None
        if sorted_rows:
            selected = sorted_rows[-1] if direction == "max" else sorted_rows[0]
            if direction == "trend":
                selected = sorted(rows, key=lambda row: (int(row["election_year"]), int(row.get("election_month") or 0)))[-1]
        return {
            "found": bool(rows),
            "sectionId": section["section_id"],
            "sectionName": section["display_name"],
            "party": party,
            "direction": direction,
            "selected": selected,
            "results": [
                {
                    "election": _election_label(row),
                    "year": row["election_year"],
                    "month": row["election_month"],
                    "votePct": float(row["vote_pct"]),
                    "votes": int(row["votes"]),
                    "validVotes": int(row["valid_votes"]),
                }
                for row in rows
            ],
        }

    def elections_party_historical_average(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        party = _normalize_party(arguments.get("party"))
        average_type = arguments.get("averageType") or "unweighted_pct"
        rows = repository.get_historical_party_average(municipality, party, limit=10)
        return {
            "party": party,
            "aggregation": arguments.get("aggregation") or "section",
            "averageType": average_type,
            "topSections": [
                {
                    "sectionId": row["section_id"],
                    "sectionName": row["section_name"],
                    "averageVotePct": float(row["average_vote_pct"]),
                    "medianVotePct": float(row["median_vote_pct"]),
                    "minVotePct": float(row["min_vote_pct"]),
                    "maxVotePct": float(row["max_vote_pct"]),
                    "electionsIncluded": int(row["number_of_elections_available"]),
                }
                for row in rows
            ],
        }

    def elections_ranking(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        party = _normalize_party(arguments.get("party"))
        year = int(arguments.get("year") or 2023)
        rows = repository.get_party_strength(municipality, party, year=year)
        return {
            "party": party,
            "year": year,
            "ranking": [
                {"section": row["section"], "votePct": float(row["percentage"])}
                for row in rows
            ],
        }

    def winner_party_by_section_set(arguments: dict[str, Any]) -> dict[str, Any]:
        section_ids = [str(section_id) for section_id in arguments.get("sectionIds", [])]
        election_type = str(arguments.get("electionType") or "municipales").lower()
        year = int(arguments.get("year") or 2023)
        rows = repository.get_winner_party_by_section_set(section_ids, election_type, year)
        return {
            "electionType": election_type,
            "year": year,
            "sections": [
                {
                    "sectionId": row["section_id"],
                    "sectionName": row["section_name"],
                    "winningParty": row["winning_party"],
                    "winningPartyLabel": row["winning_party_label"],
                    "winningVotePct": float(row["winning_vote_pct"]),
                }
                for row in rows
            ],
            "sources": ["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
        }

    def socioeconomic_similarity(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        rows = repository.get_section_similarity_profile(
            municipality,
            [str(section_id) for section_id in arguments.get("sectionIds", [])],
        )
        return {
            "compareAgainst": arguments.get("compareAgainst") or "municipality_average",
            "indicators": arguments.get("indicators") or [],
            "sections": rows,
        }

    def socioeconomic_section_profile(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        rows = repository.get_section_similarity_profile(
            municipality,
            [str(section_id) for section_id in arguments.get("sectionIds", [])],
        )
        return {"sections": rows}

    def dhondt_calculator(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        year = int(arguments.get("year") or 2023)
        seats = int(arguments.get("seats") or 25)
        threshold = float(arguments.get("thresholdPct") or 5)
        parties = repository.get_municipal_party_votes(municipality, year=year)
        result = DHondtCalculator().calculate(parties, total_seats=seats, threshold_pct=threshold)
        return {
            "year": year,
            "seats": result["seats"],
            "eligible": result["eligible"],
            "winningQuotients": [
                {"party": item.party, "divisor": item.divisor, "value": item.value}
                for item in result["winners"]
            ],
        }

    def available_datasets(arguments: dict[str, Any]) -> dict[str, Any]:
        municipality = _municipality_id(arguments.get("municipality"))
        elections = repository.get_available_elections(municipality)
        return {
            "demographicsYears": repository.get_available_demographic_years(municipality),
            "electionProcesses": [
                {
                    "type": row["election_type"],
                    "year": int(row["election_year"]),
                    "available": True,
                }
                for row in elections
            ],
            "socioeconomicYears": repository.get_available_socioeconomic_years(municipality),
            "housingYears": repository.get_available_housing_years(municipality),
        }

    municipality_property = {
        "type": "string",
        "description": "Municipality name or INE id. For Mijas use 29070.",
    }
    return ToolRegistry(
        [
            AskTool(
                "demographics_age_range",
                "Counts population in an age range using approved SocTrace demographic data.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "year": {"type": "integer"},
                        "minAge": {"type": "integer", "minimum": 0},
                        "maxAge": {"type": ["integer", "null"], "minimum": 0},
                        "gender": {"type": "string", "enum": ["H", "M", "all"]},
                        "groupBy": {"type": "string", "enum": ["municipality", "section", "gender"]},
                    },
                    ["municipality", "year", "minAge", "maxAge", "gender", "groupBy"],
                ),
                demographics_age_range,
            ),
            AskTool(
                "age_cohort_abstention_by_section",
                "Estimates abstainers and voters for an age cohort by section by combining age-range population with section abstention rates. Prefer this tool for age range + abstention/voting + sections + election questions.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "year": {"type": "integer"},
                        "electionType": {
                            "type": "string",
                            "enum": ["municipales", "andaluzas", "congreso", "europeas"],
                        },
                        "minAge": {"type": "integer", "minimum": 0},
                        "maxAge": {"type": "integer", "minimum": 0},
                        "groupBy": {"type": "string", "enum": ["section"]},
                        "sortBy": {"type": "string", "enum": ["estimated_abstainers"]},
                        "sortDirection": {"type": "string", "enum": ["desc", "asc"]},
                    },
                    [
                        "municipality",
                        "year",
                        "electionType",
                        "minAge",
                        "maxAge",
                        "groupBy",
                        "sortBy",
                        "sortDirection",
                    ],
                ),
                age_cohort_abstention_by_section,
            ),
            AskTool(
                "elections_party_section_history",
                "Returns all available election results for a normalized party in one section.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "section": {"type": "string"},
                        "party": {"type": "string"},
                        "metric": {"type": "string", "enum": ["vote_pct"]},
                        "direction": {"type": "string", "enum": ["min", "max", "trend"]},
                    },
                    ["municipality", "section", "party", "metric", "direction"],
                ),
                elections_party_section_history,
            ),
            AskTool(
                "elections_party_historical_average",
                "Calculates historical average vote percentage by section for a normalized party.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "party": {"type": "string"},
                        "aggregation": {"type": "string", "enum": ["section"]},
                        "averageType": {"type": "string", "enum": ["unweighted_pct", "weighted_by_valid_votes"]},
                    },
                    ["municipality", "party", "aggregation", "averageType"],
                ),
                elections_party_historical_average,
            ),
            AskTool(
                "elections_ranking",
                "Returns a section ranking for a party and election year.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "party": {"type": "string"},
                        "year": {"type": "integer"},
                    },
                    ["municipality", "party", "year"],
                ),
                elections_ranking,
            ),
            AskTool(
                "winner_party_by_section_set",
                "Given a set of section ids, returns the observed winning party and winning vote percentage for each section.",
                _object_schema(
                    {
                        "sectionIds": {"type": "array", "items": {"type": "string"}},
                        "electionType": {"type": "string", "enum": ["municipales", "andaluzas", "congreso", "europeas"]},
                        "year": {"type": "integer"},
                    },
                    ["sectionIds", "electionType", "year"],
                ),
                winner_party_by_section_set,
            ),
            AskTool(
                "socioeconomic_similarity",
                "Compares selected sections with available municipal socioeconomic indicators.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "sectionIds": {"type": "array", "items": {"type": "string"}},
                        "compareAgainst": {"type": "string", "enum": ["municipality_average"]},
                        "indicators": {"type": "array", "items": {"type": "string"}},
                    },
                    ["municipality", "sectionIds", "compareAgainst", "indicators"],
                ),
                socioeconomic_similarity,
            ),
            AskTool(
                "socioeconomic_section_profile",
                "Returns available socioeconomic profile fields for selected sections.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "sectionIds": {"type": "array", "items": {"type": "string"}},
                    },
                    ["municipality", "sectionIds"],
                ),
                socioeconomic_section_profile,
            ),
            AskTool(
                "dhondt_calculator",
                "Calculates the municipal D'Hondt seat allocation from observed SocTrace votes.",
                _object_schema(
                    {
                        "municipality": municipality_property,
                        "year": {"type": "integer"},
                        "seats": {"type": "integer"},
                        "thresholdPct": {"type": "number"},
                    },
                    ["municipality", "year", "seats", "thresholdPct"],
                ),
                dhondt_calculator,
            ),
            AskTool(
                "available_datasets",
                "Lists available demographic, electoral, socioeconomic and housing datasets.",
                _object_schema({"municipality": municipality_property}, ["municipality"]),
                available_datasets,
            ),
        ]
    )
