from dataclasses import dataclass
import re
import unicodedata

from app.ask.section_reference import detect_section_references
from app.ask.sql import QueryExecutor
from app.schemas.ask import AskRequest, AskResponse


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )


def _election_type(text: str) -> str | None:
    if re.search(r"\bmunicipal(?:es)?\b", text):
        return "MUNICIPALES"
    if re.search(r"\b(congreso|generales)\b", text):
        return "CONGRESO"
    if re.search(r"\b(europeas|parlamento europeo)\b", text):
        return "PARLAMENTO_EUROPEO"
    if re.search(r"\b(andaluzas|autonomicas)\b", text):
        return "ANDALUZAS"
    return None


@dataclass(frozen=True, slots=True)
class ParticipationTrendResolution:
    response: AskResponse
    tool_name: str
    tool_arguments: dict[str, object]


def resolve_participation_trend(
    payload: AskRequest,
    query_executor: QueryExecutor,
) -> ParticipationTrendResolution | None:
    question = payload.question or ""
    text = _normalize(question)
    if not re.search(r"\bparticipacion\b", text):
        return None
    temporal = bool(
        re.search(r"\b(evolucion|evolucionado|tendencia|historica|por anos)\b", text)
        or re.search(r"\bdesde\s+20\d{2}\b", text)
        or re.search(r"\bentre\s+20\d{2}\s+y\s+20\d{2}\b", text)
    )
    if not temporal:
        return None

    detection = detect_section_references(question)
    if len(detection.section_ids) > 1:
        return None
    requested_section = detection.selected_section_id
    municipality_id = payload.activeMunicipality or "29070"
    election_type = _election_type(text)

    range_match = re.search(r"\bentre\s+(20\d{2})\s+y\s+(20\d{2})\b", text)
    since_match = re.search(r"\bdesde\s+(20\d{2})\b", text)
    until_match = re.search(r"\b(?:hasta|a)\s+(20\d{2})\b", text)
    if range_match:
        start_year = int(range_match.group(1))
        end_year = int(range_match.group(2))
    else:
        start_year = int(since_match.group(1)) if since_match else None
        end_year = int(until_match.group(1)) if until_match else None

    parameters: dict[str, object] = {"municipio_id": municipality_id}
    filters: list[str] = ["summary.municipio_id = :municipio_id"]
    if start_year is not None:
        filters.append("summary.election_year >= :start_year")
        parameters["start_year"] = start_year
    if end_year is not None:
        filters.append("summary.election_year <= :end_year")
        parameters["end_year"] = end_year
    if election_type is not None:
        filters.append("summary.election_type = :election_type")
        parameters["election_type"] = election_type

    target_cte = ""
    target_join = ""
    if requested_section is not None:
        target_cte = """
WITH target AS (
    SELECT section_id
    FROM marts.agent_section_lookup
    WHERE municipio_id = :municipio_id
      AND section_number = :section_number
    ORDER BY section_name
    LIMIT 1
)
"""
        target_join = "JOIN target ON target.section_id = summary.section_id"
        parameters["section_number"] = str(int(requested_section)).zfill(2)

    sql = f"""
{target_cte}SELECT
    summary.election_year,
    summary.election_type,
    summary.election_id,
    MAX(summary.election_label) AS election_label,
    ROUND(SUM(summary.total_votes)::numeric / NULLIF(SUM(summary.census), 0) * 100, 2) AS participation_pct,
    SUM(summary.total_votes)::bigint AS total_votes,
    SUM(summary.census)::bigint AS census
FROM marts.agent_electoral_summary AS summary
{target_join}
WHERE {' AND '.join(filters)}
  AND summary.total_votes IS NOT NULL
  AND summary.census IS NOT NULL
GROUP BY summary.election_year, summary.election_type, summary.election_id
ORDER BY summary.election_year, summary.election_type, summary.election_id
""".strip()
    rows = query_executor.execute(sql, parameters)

    scope = f"sección {requested_section}" if requested_section else "Mijas"
    if not rows:
        response = AskResponse(
            answer=f"No hay datos de participación electoral para {scope} en el periodo solicitado.",
            confidence="low",
            resultType="time_series",
            data={
                "tool": "participation_trend",
                "operation": "participation_trend",
                "territorial_scope": "section" if requested_section else "municipality",
                "requested_section_id": requested_section,
                "start_year": start_year,
                "end_year": end_year,
                "election_type": election_type,
                "rows": [],
            },
            sources=["marts.agent_electoral_summary"],
        )
        return ParticipationTrendResolution(response, "participation_trend", parameters)

    first_value = float(rows[0]["participation_pct"])
    last_value = float(rows[-1]["participation_pct"])
    delta = round(last_value - first_value, 2)
    direction = "aumentó" if delta > 0 else "disminuyó" if delta < 0 else "se mantuvo estable"
    series = "; ".join(
        f"{row['election_year']} {row['election_type']}: {float(row['participation_pct']):.2f}%"
        for row in rows
    )
    answer = (
        f"La participación electoral en {scope} {direction} {abs(delta):.2f} puntos porcentuales "
        f"entre el primer y el último proceso disponibles. Serie cronológica: {series}."
    )
    response = AskResponse(
        answer=answer,
        confidence="high",
        resultType="time_series",
        data={
            "tool": "participation_trend",
            "operation": "participation_trend",
            "territorial_scope": "section" if requested_section else "municipality",
            "requested_section_id": requested_section,
            "start_year": start_year,
            "end_year": end_year,
            "election_type": election_type,
            "direction": direction,
            "delta_pp": delta,
            "rows": rows,
        },
        chartSpec={
            "type": "line",
            "x": "election_year",
            "y": "participation_pct",
            "series": "election_type",
        },
        sources=["marts.agent_electoral_summary"],
    )
    return ParticipationTrendResolution(
        response=response,
        tool_name="participation_trend",
        tool_arguments={
            "municipio_id": municipality_id,
            "section": requested_section,
            "start_year": start_year,
            "end_year": end_year,
            "election_type": election_type,
        },
    )
