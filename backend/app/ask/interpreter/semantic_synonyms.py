from dataclasses import dataclass, field
import re
from typing import Any

from app.ask.interpreter.intent_schema import AnalyticalIntent, TimeScope
from app.services.local_analyst_service import extract_party, normalize


@dataclass(frozen=True, slots=True)
class SynonymRule:
    patterns: tuple[str, ...]
    metric: str
    direction: str
    intent: str = "single_extreme"
    filters: dict[str, Any] = field(default_factory=dict)
    derived_logic: str | None = None
    time_scope: TimeScope | None = None


SYNONYM_RULES: tuple[SynonymRule, ...] = (
    SynonymRule(
        patterns=(
            r"\bmayor numero de jovenes\b",
            r"\bmayor numero de personas jovenes\b",
            r"\bmas jovenes\b",
            r"\bmas poblacion joven\b",
            r"\bmas menores de 30\b",
        ),
        metric="population_under_30",
        direction="max",
    ),
    SynonymRule(
        patterns=(
            r"\bmayor porcentaje de jovenes\b",
            r"\bporcentaje de jovenes\b",
            r"\bporcentaje de menores de 30\b",
        ),
        metric="population_under_30_pct",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmayor porcentaje de mayores de 65\b", r"\bporcentaje de mayores de 65\b"),
        metric="population_over_65_pct",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmas mayores de 65\b", r"\bmayor numero de mayores\b", r"\bmas poblacion mayor\b"),
        metric="population_over_65",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmas joven\b", r"\byoungest\b", r"\byounger\b", r"\bzonas jovenes\b"),
        metric="average_age",
        direction="min",
    ),
    SynonymRule(
        patterns=(r"\bmas envejecida\b", r"\boldest\b", r"\bolder\b", r"\bmas mayor\b", r"\bmas senior\b"),
        metric="average_age",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmas poblacion\b", r"\bmas habitantes\b", r"\blargest population\b"),
        metric="population_total",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmenos poblacion\b", r"\bleast populated\b", r"\bmenor poblacion\b"),
        metric="population_total",
        direction="min",
    ),
    SynonymRule(
        patterns=(r"\bmas rica\b", r"\brenta mas alta\b", r"\bhighest income\b", r"\bwealthiest\b"),
        metric="income_individual",
        direction="max",
    ),
    SynonymRule(
        patterns=(r"\bmas pobre\b", r"\brenta mas baja\b", r"\blowest income\b", r"\bmenor renta\b"),
        metric="income_individual",
        direction="min",
    ),
    SynonymRule(
        patterns=(r"\bmas abstencion\b", r"\babstention peak\b", r"\bno votaron mas\b", r"\bdonde hay mas abstencion\b"),
        metric="abstention_pct",
        direction="max",
        time_scope=TimeScope(electionType="municipales"),
    ),
    SynonymRule(
        patterns=(r"\bmas participacion\b", r"\bturnout highest\b", r"\bvotaron mas\b"),
        metric="participation_pct",
        direction="max",
        time_scope=TimeScope(electionType="municipales"),
    ),
    SynonymRule(
        patterns=(r"\bgana siempre\b", r"\bsiempre gana\b", r"\bwins always\b", r"\bprimera fuerza siempre\b", r"\bfuerza .* siempre\b"),
        metric="persistent_winner",
        direction="max",
        intent="derived_metric",
        derived_logic="winner_count equals total elections checked",
        time_scope=TimeScope(allAvailable=True),
    ),
)


def deterministic_intent(question: str, default_municipality: str = "Mijas") -> AnalyticalIntent | None:
    text = normalize(question)
    party = extract_party(question)

    if party and re.search(r"\b(mas fuerte|strongest|donde.*fuerte|where.*strongest)\b", text):
        return AnalyticalIntent(
            intent="single_extreme",
            entity="section",
            metric="vote_pct",
            direction="max",
            filters={"municipality": default_municipality, "party": party},
            groupBy=["section"],
            timeScope=TimeScope(electionType="municipales"),
            confidence="high",
        )

    for rule in SYNONYM_RULES:
        if any(re.search(pattern, text) for pattern in rule.patterns):
            filters = {"municipality": default_municipality, **rule.filters}
            if rule.metric == "persistent_winner":
                filters["party"] = party or "PSOE"
            return AnalyticalIntent(
                intent=rule.intent,
                entity="section",
                metric=rule.metric,
                direction=rule.direction,
                filters=filters,
                groupBy=["section"],
                timeScope=rule.time_scope or TimeScope(),
                derivedLogic=rule.derived_logic,
                confidence="high",
            )

    return None
