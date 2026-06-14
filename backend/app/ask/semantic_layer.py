from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Literal

import yaml

from app.services.local_analyst_service import extract_party, normalize
from app.ask.conversation.conversational_policy import ConversationalPolicyLayer
from app.ask.conversation.context_inheritance_policy import ContextInheritancePolicy


AnalyticalOperationName = Literal[
    "rank_sections",
    "aggregate_municipality",
    "compare_years",
    "filter_sections",
    "section_profile",
    "party_strength",
    "persistent_winner",
    "historical_party_average",
    "age_cohort_projection",
    "ecological_vote_profile_by_age_group",
    "electoral_viability_estimate",
    "electoral_growth_opportunity",
    "mobilizable_abstention_opportunity",
    "population_growth",
    "cross_metric_ranking",
    "correlation_analysis",
]


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    label: str
    description: str
    view: str
    field: str
    entity: str = "section"
    type: str = "numeric"
    default_operation: str = "rank_sections"
    default_order: str = "desc"
    synonyms_es: tuple[str, ...] = ()
    synonyms_en: tuple[str, ...] = ()
    supported_operations: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    requires_party: bool = False
    pending: bool = False

    @property
    def synonyms(self) -> tuple[str, ...]:
        return self.synonyms_es + self.synonyms_en


@dataclass(frozen=True, slots=True)
class AnalyticalOperation:
    operation: AnalyticalOperationName
    metric: str | None = None
    metrics: list[str] = field(default_factory=list)
    entity: str = "section"
    municipio_id: str = "29070"
    municipality_id: str = "29070"
    year: int | None = None
    election_type: str | None = None
    election_year: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    party: str | None = None
    rank_by: str | None = None
    direction: str | None = None
    order: Literal["asc", "desc"] = "desc"
    limit: int = 1
    output: Literal["single_entity", "entity_list", "table", "explanation", "single_value"] = "single_entity"
    filters: dict[str, Any] = field(default_factory=dict)
    confidence: Literal["high", "medium", "low"] = "high"
    supported: bool = True
    reason: str | None = None
    explanation: str = ""
    response_hint: dict[str, Any] = field(default_factory=dict)


class SemanticCatalog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parent / "semantic_catalog.yaml"
        self.raw: dict[str, Any] = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.metrics = self._load_metrics()

    @property
    def approved_relations(self) -> set[str]:
        relations = {
            item["source"]
            for item in self.raw.get("views", {}).values()
            if item.get("source")
        }
        relations.update(metric.view for metric in self.metrics.values() if metric.view)
        return relations

    @property
    def operations(self) -> dict[str, Any]:
        return self.raw.get("operations", {})

    def _load_metrics(self) -> dict[str, MetricDefinition]:
        metrics: dict[str, MetricDefinition] = {}
        for metric_id, item in (self.raw.get("metrics") or {}).items():
            metrics[metric_id] = MetricDefinition(
                metric_id=metric_id,
                label=str(item.get("label") or metric_id),
                description=str(item.get("description") or ""),
                view=str(item.get("view") or ""),
                field=str(item.get("field") or metric_id),
                entity=str(item.get("entity") or "section"),
                type=str(item.get("type") or "numeric"),
                default_operation=str(item.get("default_operation") or "rank_sections"),
                default_order=str(item.get("default_order") or "desc"),
                synonyms_es=tuple(str(value) for value in item.get("synonyms_es") or []),
                synonyms_en=tuple(str(value) for value in item.get("synonyms_en") or []),
                supported_operations=tuple(str(value) for value in item.get("supported_operations") or []),
                caveats=tuple(str(value) for value in item.get("caveats") or []),
                requires_party=metric_id == "vote_pct",
                pending=bool(item.get("pending")),
            )
        return metrics

    def metric(self, metric_id: str | None) -> MetricDefinition | None:
        if not metric_id:
            return None
        return self.metrics.get(metric_id)

    def match_metric(self, question: str) -> MetricDefinition | None:
        text = normalize(question)
        best: tuple[int, MetricDefinition] | None = None
        for metric in self.metrics.values():
            if metric.pending:
                continue
            for synonym in metric.synonyms:
                pattern = normalize(synonym)
                if pattern and re.search(rf"\b{re.escape(pattern)}\b", text):
                    score = len(pattern)
                    if best is None or score > best[0]:
                        best = (score, metric)
        return best[1] if best else None


class SemanticOperationInterpreter:
    def __init__(self, catalog: SemanticCatalog | None = None) -> None:
        self.catalog = catalog or SemanticCatalog()
        self.conversational_policy = ConversationalPolicyLayer()
        self.inheritance_policy = ContextInheritancePolicy()

    def interpret(
        self,
        question: str,
        *,
        municipio_id: str = "29070",
        active_year: int | None = None,
        last_metric: str | None = None,
        last_party: str | None = None,
    ) -> AnalyticalOperation | None:
        text = normalize(question)
        explicit_party = extract_party(question)
        party = explicit_party or last_party
        limit = self._limit(question)
        asks_for_list = limit > 1 or bool(re.search(r"que secciones|qué secciones|donde|zonas|areas|ranking|lista|ordena|cuales|cu[aá]les", text))
        year = self._year(question) or active_year
        election_type = "MUNICIPALES" if re.search(r"municipales|alcald|ayuntamiento|abstencion|participacion|voto|gana|fuerte|disputad", text) else None

        policy_decision = self.conversational_policy.resolve(
            question,
            semantic_interpretation=None,
            conversation_context={"last_party": last_party},
        )
        if policy_decision.action in {"proxy_analysis", "scenario_estimate"} and policy_decision.preferred_tool == "electoral_viability_estimate":
            return self._operation(
                "electoral_viability_estimate",
                "electoral_viability",
                municipio_id,
                party=str(policy_decision.preferred_arguments.get("party") or party or "ALL"),
                election_type=str(policy_decision.preferred_arguments.get("election_type") or "MUNICIPALES"),
                year=year,
                output="table",
                confidence=policy_decision.confidence,
                explanation=policy_decision.explanation_to_user or "Uso una estimacion orientativa de viabilidad electoral.",
            )
        if policy_decision.action == "proxy_analysis" and policy_decision.preferred_tool == "electoral_growth_opportunity":
            return self._operation(
                "electoral_growth_opportunity",
                "electoral_growth_opportunity",
                municipio_id,
                party=str(policy_decision.preferred_arguments.get("party") or party or "PP"),
                election_type=str(policy_decision.preferred_arguments.get("election_type") or "MUNICIPALES"),
                year=year,
                limit=limit if asks_for_list else 8,
                output="entity_list",
                confidence=policy_decision.confidence,
                explanation=policy_decision.explanation_to_user or "Uso una estimacion de oportunidad de crecimiento electoral.",
            )
        if policy_decision.action == "proxy_analysis" and policy_decision.preferred_tool == "mobilizable_abstention_opportunity":
            target = str(policy_decision.preferred_arguments.get("target") or "general")
            return self._operation(
                "mobilizable_abstention_opportunity",
                "mobilizable_abstention",
                municipio_id,
                election_type=str(policy_decision.preferred_arguments.get("election_type") or "MUNICIPALES"),
                year=year,
                filters={"target": target},
                limit=limit if asks_for_list else 10,
                output="entity_list",
                confidence=policy_decision.confidence,
                explanation=policy_decision.explanation_to_user or "Uso una estimacion de abstencion movilizable por seccion.",
            )

        mobilizable_target = self._mobilizable_abstention_target(text, explicit_party, last_party, question)
        if mobilizable_target:
            return self._operation(
                "mobilizable_abstention_opportunity",
                "mobilizable_abstention",
                municipio_id,
                election_type=election_type or "MUNICIPALES",
                year=year,
                filters={"target": mobilizable_target},
                limit=limit if asks_for_list else 10,
                output="entity_list",
                confidence="high",
                explanation="Reconozco una consulta de abstencion movilizable y la traduzco a un indice territorial de oportunidad.",
            )

        correlation_metrics = self._correlation_metrics(text)
        if correlation_metrics:
            return self._operation(
                "correlation_analysis",
                correlation_metrics[0],
                municipio_id,
                metrics=correlation_metrics,
                year=year,
                limit=50,
                output="entity_list",
                confidence="medium",
                explanation="Reconozco una relacion estadistica beta entre dos metricas.",
            )

        threshold = self._population_threshold(text)
        if threshold is not None:
            return self._operation(
                "filter_sections",
                "population_total",
                municipio_id,
                filters={"conditions": [{"metric": "population_total", "operator": ">", "value": threshold}]},
                year=year,
                limit=50,
                output="entity_list",
                explanation=f"Reconozco un filtro de secciones con poblacion superior a {threshold}.",
            )

        aggregate = self._aggregate_metric(text)
        if aggregate:
            return self._operation(
                "aggregate_municipality",
                aggregate,
                municipio_id,
                year=year,
                output="single_value",
                limit=1,
                explanation=f"Reconozco una agregacion municipal de {aggregate}.",
            )

        age_range = self._age_range_count(question)
        if age_range:
            start_age, end_age = age_range
            return self._operation(
                "aggregate_municipality",
                "population_total",
                municipio_id,
                year=year,
                output="single_value",
                filters={"age_min": start_age, "age_max": end_age},
                explanation=f"Reconozco una agregacion municipal por edad {start_age}-{end_age}.",
            )

        relative_age_metric = self._relative_age_metric(text)
        if relative_age_metric:
            if re.search(r"cada seccion|cada sección|por seccion|por sección|secciones|zonas|donde|en que seccion|en qué sección", text):
                return self._operation(
                    "rank_sections",
                    relative_age_metric,
                    municipio_id,
                    year=year,
                    order="desc",
                    limit=limit if asks_for_list else 1,
                    output="entity_list" if asks_for_list else "single_entity",
                    explanation=f"Reconozco que la pregunta pide valor relativo y uso {relative_age_metric}.",
                )
            return self._operation(
                "aggregate_municipality",
                relative_age_metric,
                municipio_id,
                year=year,
                output="single_value",
                limit=1,
                explanation=f"Reconozco un porcentaje municipal y uso {relative_age_metric}.",
            )

        if self._asks_future_age_cohort_projection(text):
            target_year = year or 2027
            target_age = self._target_age(question) or 18
            source_year = target_year - 2
            source_age = max(target_age - 2, 0)
            return self._operation(
                "age_cohort_projection",
                "population_total",
                municipio_id,
                year=target_year,
                rank_by="estimated_future_age_population",
                order="desc",
                limit=limit if asks_for_list else 5,
                output="entity_list",
                filters={
                    "sourceYear": source_year,
                    "sourceAge": source_age,
                    "targetYear": target_year,
                    "targetAge": target_age,
                    "groupBy": "municipality_and_section",
                },
                confidence="medium",
                explanation="Proyecto una cohorte de edad desde el ano fuente al ano objetivo.",
            )

        age_vote_filters = self._age_vote_profile_filters(text)
        if age_vote_filters:
            return self._operation(
                "ecological_vote_profile_by_age_group",
                "vote_pct",
                municipio_id,
                year=year,
                election_type=election_type or "MUNICIPALES",
                election_year=year,
                order="desc",
                limit=10,
                output="table",
                filters=age_vote_filters,
                confidence="medium",
                explanation="Reconozco una pregunta de voto por grupo de edad y la traduzco a inferencia ecologica territorial.",
            )

        cross_metrics, cross_directions, cross_explanation = self._cross_metric_metrics(text, party)
        if cross_metrics:
            return self._operation(
                "cross_metric_ranking",
                cross_metrics[0],
                municipio_id,
                metrics=cross_metrics,
                party=party,
                filters={"metric_directions": cross_directions},
                limit=10,
                output="entity_list",
                confidence="medium",
                explanation=cross_explanation or "Reconozco una combinacion de metricas para ranking compuesto.",
            )

        if self._asks_age_change(text):
            direction = "largest_decrease" if re.search(r"rejuvenec", text) else "largest_increase"
            return self._operation(
                "compare_years",
                "average_age",
                municipio_id,
                start_year=self._year(question) or 2021,
                end_year=None,
                direction=direction,
                order="asc" if direction == "largest_decrease" else "desc",
                limit=limit if asks_for_list else 1,
                output="entity_list" if asks_for_list else "single_entity",
                explanation="Reconozco una comparacion temporal de edad media.",
            )

        growth_metric = self._growth_metric(question)
        if growth_metric:
            start_year, end_year = self._year_range(question)
            return self._operation(
                "population_growth",
                "population_total",
                municipio_id,
                start_year=start_year,
                end_year=end_year,
                rank_by="growth_pct" if growth_metric == "population_growth_pct" else "growth_abs",
                order="asc" if self._asks_population_loss(question) else "desc",
                limit=limit if asks_for_list else 5,
                output="entity_list",
                explanation="Reconozco una comparacion temporal de poblacion por seccion.",
            )

        if re.search(r"gana.*siempre|siempre.*gana|primera fuerza siempre|wins always", text):
            return self._operation(
                "persistent_winner",
                "winner_party",
                municipio_id,
                party=party or "PP",
                order="desc",
                limit=50,
                output="entity_list",
                election_type=election_type,
                explanation="Reconozco una busqueda de ganador persistente en elecciones disponibles.",
            )

        if party and re.search(r"mas fuerte|más fuerte|donde.*fuerte|voto al|voto a|favorable|strongest", text):
            return self._operation(
                "party_strength",
                "vote_pct",
                municipio_id,
                party=party,
                election_type=election_type or "MUNICIPALES",
                election_year=year,
                order="desc",
                limit=limit if asks_for_list else 1,
                output="entity_list" if asks_for_list else "single_entity",
                explanation=f"Reconozco fortaleza electoral del partido {party}.",
            )

        if re.search(r"historicamente|hist[oó]ricamente|media historica|media hist[oó]rica|domina histor", text):
            return self._operation(
                "historical_party_average",
                "vote_pct",
                municipio_id,
                party=party,
                election_type=election_type or "MUNICIPALES",
                limit=10,
                output="entity_list",
                explanation="Reconozco una media historica electoral.",
            )

        metric = self.catalog.match_metric(question)
        if re.search(r"\ben porcentaje\b|porcentaje|porcentual|valor relativo|peso relativo|proporcion|proporción|share|pct|%", text) and last_metric:
            metric = self.catalog.metric(_relative_metric_id(last_metric)) or metric
        if not metric and re.search(r"\ben porcentaje\b|%", text) and last_metric:
            metric = self.catalog.metric(f"{last_metric}_pct") or self.catalog.metric(last_metric)
        if not metric:
            return None

        order = self._direction(question, metric)
        if metric.requires_party and not party:
            return self._unsupported(
                metric.metric_id,
                municipio_id,
                f"He reconocido `{metric.metric_id}`, pero falta el partido necesario para consultar voto.",
            )
        return self._operation(
            "rank_sections",
            metric.metric_id,
            municipio_id,
            year=year,
            election_type=election_type,
            election_year=year,
            party=party,
            order=order,
            limit=limit if asks_for_list else 1,
            output="entity_list" if asks_for_list else "single_entity",
            explanation=f"Mapeo la pregunta a un ranking de secciones por `{metric.metric_id}`.",
        )

    def fallback_message(self, question: str) -> str:
        text = normalize(question)
        if re.search(r"extranj", text):
            return "Entiendo que preguntas por población extranjera, pero esa métrica no está en Semantic Layer v2."
        metric = self.catalog.match_metric(question)
        if metric:
            return f"He reconocido `{metric.metric_id}`, pero no he encontrado una operacion v2 aplicable a la forma de la pregunta."
        if re.search(r"correlacion|relacion|clustering|agrupa|predic", text):
            return "Reconozco una tecnica analitica avanzada, pero esta marcada como pending en Semantic Layer v2."
        if re.search(r"vivienda|inmobili|residencial|parcel", text):
            return "Entiendo que preguntas por vivienda o presion residencial, pero no he reconocido una metrica concreta del catalogo v2."
        if re.search(r"poblacion|habitantes|edad|joven|mayor|jubil", text):
            return "Entiendo que preguntas por poblacion, pero no encuentro una metrica v2 compatible en el catalogo semantico."
        if re.search(r"voto|partido|abstencion|participacion|gana", text):
            return (
                "No tengo una probabilidad exacta porque falta una capa de sondeos actuales, "
                "pero puedo estimar la fortaleza electoral con los datos históricos y territoriales disponibles."
            )
        return "No encuentro una operacion analitica aprobada en Semantic Layer v2 para responder con datos internos de soctrace."

    def _operation(self, operation: AnalyticalOperationName, metric: str, municipio_id: str, **kwargs: Any) -> AnalyticalOperation:
        definition = self.catalog.metric(metric)
        response_hint = self._response_hint(operation, definition, kwargs.get("output"), kwargs.get("metrics"))
        return AnalyticalOperation(
            operation=operation,
            metric=metric,
            entity=definition.entity if definition else "section",
            municipio_id=municipio_id,
            municipality_id=municipio_id,
            response_hint=response_hint,
            **kwargs,
        )

    def _unsupported(self, metric: str, municipio_id: str, reason: str) -> AnalyticalOperation:
        return AnalyticalOperation(
            operation="rank_sections",
            metric=metric,
            municipio_id=municipio_id,
            municipality_id=municipio_id,
            supported=False,
            confidence="low",
            reason=reason,
            explanation=reason,
        )

    def _response_hint(
        self,
        operation: str,
        metric: MetricDefinition | None,
        output: str | None,
        metrics: list[str] | None,
    ) -> dict[str, Any]:
        label = metric.label.lower() if metric else "metrica"
        if operation == "cross_metric_ranking":
            label = " + ".join(metrics or [])
        return {
            "answer_type": "ranking" if output in {"entity_list", "single_entity"} else output or "ranking",
            "value_label": label,
            "methodology_plain": f"Uso las vistas agent_* aprobadas y comparo {label} segun la operacion {operation}.",
            "suggested_followups": [
                "¿Puedes mostrarlo en porcentaje?",
                "¿Que otras secciones aparecen en el ranking?",
            ],
        }

    def _direction(self, question: str, metric: MetricDefinition) -> Literal["asc", "desc"]:
        text = normalize(question)
        if metric.metric_id == "margin_pct" and re.search(r"disputad|competitividad", text):
            return "asc"
        if metric.metric_id == "average_age" and re.search(r"joven|youngest|younger", text):
            return "asc"
        if metric.metric_id == "average_age" and re.search(r"envejec|oldest|older", text):
            return "desc"
        if metric.metric_id in {"population_under_18", "population_under_18_pct", "population_under_30", "population_under_30_pct"} and re.search(r"menor(?:es)? de", text):
            return "desc"
        if re.search(r"menor|menos|baja|bajo|pobre|lowest|least", text):
            return "asc"
        return "asc" if metric.default_order in {"asc", "min"} else "desc"

    def _limit(self, question: str) -> int:
        text = normalize(question)
        match = re.search(r"\b(?:top|primeras|primeros|dame las|dame los|muestrame|mu[eé]strame)\s+(\d{1,2})\b", text)
        if match:
            return max(1, min(int(match.group(1)), 50))
        if re.search(r"ranking|lista|ordena|todas|todos|que secciones|qué secciones|donde|zonas|areas|cuales|cu[aá]les", text):
            return 10
        return 1

    def _year(self, question: str) -> int | None:
        match = re.search(r"\b(20\d{2}|19\d{2})\b", question)
        return int(match.group(1)) if match else None

    def _target_age(self, question: str) -> int | None:
        text = normalize(question)
        match = re.search(r"(?:tendran|tendrán|cumpliran|cumplirán|tener)\s+(\d{1,3})", text)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(\d{1,3})\s*(?:anos|años)\s+en\s+20\d{2}", text)
        return int(match.group(1)) if match else None

    def _relative_age_metric(self, text: str) -> str | None:
        if not re.search(r"porcentaje|porcentual|valor relativo|peso relativo|proporcion|proporción|share|pct|%", text):
            return None
        if re.search(r"mayores de 65|mayores|jubilad|senior", text):
            return "population_over_65_pct"
        if re.search(r"menores de 18|menores de edad", text):
            return "population_under_18_pct"
        if re.search(r"menores de 30|joven|jovenes|jóvenes", text):
            return "population_under_30_pct"
        return None

    def _asks_future_age_cohort_projection(self, text: str) -> bool:
        return bool(
            re.search(r"tendran\s+18|tendrán\s+18|18\s+anos\s+en\s+2027|18\s+años\s+en\s+2027", text)
            or re.search(r"podran\s+votar|podrán\s+votar|primer voto|votar por primera vez|nuevos votantes|nuevas votantes", text)
        )

    def _age_vote_profile_filters(self, text: str) -> dict[str, Any] | None:
        asks_vote_behavior = bool(
            re.search(r"que\s+votan|qu[eé]\s+votan|suelen\s+votar|voto\s+de|partido\s+entre|que\s+partido|qu[eé]\s+partido|domina", text)
        )
        if not asks_vote_behavior:
            return None
        age_group = self._parse_age_group(text)
        if not age_group:
            return None
        return age_group

    def _parse_age_group(self, text: str) -> dict[str, Any] | None:
        match = re.search(r"mayores\s+de\s+(\d{1,3})", text)
        if match:
            return {"age_min": int(match.group(1)), "age_max": None}
        match = re.search(r"menores\s+de\s+(\d{1,3})", text)
        if match:
            return {"age_min": None, "age_max": int(match.group(1))}
        if re.search(r"joven|jovenes|jóvenes|voto joven", text):
            return {"age_min": None, "age_max": 30}
        if re.search(r"mayores|personas mayores|jubilad", text):
            return {"age_min": 65, "age_max": None}
        return None

    def _age_range_count(self, question: str) -> tuple[int, int] | None:
        text = normalize(question)
        match = re.search(r"entre\s+(\d{1,3})\s+y\s+(\d{1,3})\s+anos", text)
        if match and re.search(r"cuantas|cu[aá]ntas|personas", text):
            return int(match.group(1)), int(match.group(2))
        return None

    def _aggregate_metric(self, text: str) -> str | None:
        if not re.search(r"mijas|municipio|municipal", text):
            return None
        if re.search(r"poblacion total|habitantes", text):
            return "population_total"
        if re.search(r"mayores de 65|jubilados|personas mayores", text):
            return "population_over_65"
        if re.search(r"joven|menores de 30", text):
            return "population_under_30_pct" if re.search(r"porcentaje|%", text) else "population_under_30"
        return None

    def _mobilizable_abstention_target(self, text: str, explicit_party: str | None, last_party: str | None, question: str) -> str | None:
        asks_mobilizable = bool(re.search(
            r"abstencion movilizable|abstenci[oó]n movilizable|bolsa de abstencion|bolsa de abstenci[oó]n|"
            r"abstencionistas potenciales|movilizar abstencion|movilizar abstenci[oó]n|"
            r"voto abstencionista movilizable|abstencion activable|abstenci[oó]n activable|"
            r"donde hay mas abstencionistas|d[oó]nde hay m[aá]s abstencionistas|"
            r"priorizar.*campa[nñ]a.*moviliz|zonas.*priorizar.*campa[nñ]a",
            text,
        ))
        context = {"last_party": last_party, "lastParty": last_party}
        explicit_target = self.inheritance_policy.explicit_target(question)
        inherit_party = self.inheritance_policy.should_inherit_party(question, context)
        explicit_followup = bool(explicit_target and re.fullmatch(r"(?:y\s+)?para\s+.+", text.strip(" ¿?!.")))
        if not asks_mobilizable and not explicit_followup and not inherit_party:
            return None
        if explicit_target:
            return explicit_target
        if inherit_party and last_party in {"PP", "PSOE", "VOX"}:
            return last_party
        return "general"

    def _population_threshold(self, text: str) -> int | None:
        if not re.search(r"superan|m[aá]s de\s+\d|por encima|mayor(?:es)? que", text):
            return None
        match = re.search(r"(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})\s*(?:habitantes|personas)?", text)
        return int(re.sub(r"\D", "", match.group(1))) if match else None

    def _asks_age_change(self, text: str) -> bool:
        return bool(re.search(r"ha rejuvenec|rejuvenecimiento|ha envejec|envejecimiento|evolucion de la edad", text))

    def _year_range(self, question: str) -> tuple[int | None, int | None]:
        years = [int(match) for match in re.findall(r"\b(20\d{2}|19\d{2})\b", question)]
        if len(years) >= 2:
            return min(years[0], years[1]), max(years[0], years[1])
        if len(years) == 1:
            return years[0], None
        return None, None

    def _growth_metric(self, question: str) -> str | None:
        text = normalize(question)
        if not re.search(r"crecid|crecimiento|aumentad|ganado|perdid|perdido|decrecid|decrecimiento|growth|grown|lost", text):
            return None
        if not re.search(r"poblacion|habitantes|demograf|zonas|secciones|areas", text):
            return None
        return "population_growth_pct" if re.search(r"porcentaje|porcentual|relativ|proporcion|%", text) else "population_growth_abs"

    def _asks_population_loss(self, question: str) -> bool:
        text = normalize(question)
        return bool(re.search(r"perdid|perdido|pierden|decrecid|decrecimiento|descens|lost|declin", text))

    def _cross_metric_metrics(self, text: str, party: str | None) -> tuple[list[str] | None, dict[str, str], str | None]:
        if re.search(r"polarizacion demografica|polarizaci[oó]n demogr[aá]fica", text):
            return (
                ["population_under_30_pct", "population_over_65_pct"],
                {"population_under_30_pct": "high", "population_over_65_pct": "high"},
                "Reconozco polarizacion demografica como convivencia intensa de poblacion joven y poblacion mayor.",
            )
        if re.search(r"homogene", text):
            return (
                ["population_under_30_pct", "population_over_65_pct"],
                {"population_under_30_pct": "low", "population_over_65_pct": "low"},
                "Reconozco homogeneidad demografica como menor peso relativo de extremos de edad.",
            )
        if re.search(r"oportunidad(?:es)? inmobiliaria|infravalorad", text):
            return (
                ["market_to_cadastral_ratio", "residential_pressure_index"],
                {"market_to_cadastral_ratio": "low", "residential_pressure_index": "low"},
                "Reconozco oportunidad inmobiliaria como menor brecha mercado-catastro y menor presion residencial relativa.",
            )
        if re.search(r"potencial de revalorizacion|potencial de revalorizaci[oó]n|revaloriza", text):
            return (
                ["market_to_cadastral_ratio", "building_intensity"],
                {"market_to_cadastral_ratio": "low", "building_intensity": "high"},
                "Reconozco potencial de revalorizacion como margen de valor relativo combinado con intensidad territorial.",
            )
        has_combo = bool(re.search(r"combinan|combina|y menos|y alta|y alto|relacion", text))
        if not has_combo:
            return None, {}, None
        metrics: list[str] = []
        directions: dict[str, str] = {}
        if re.search(r"renta baja|menos renta|baja renta|pobre", text):
            metrics.append("income_individual")
            directions["income_individual"] = "low"
        if re.search(r"renta alta|alta renta|ricos", text):
            metrics.append("income_individual")
            directions["income_individual"] = "high"
        if re.search(r"abstencion|abstención", text):
            metrics.append("abstention_pct")
            directions["abstention_pct"] = "high"
        if re.search(r"izquierda|izquierdas|progresista|bloque progresista", text):
            metrics.append("left_bloc_pct")
            directions["left_bloc_pct"] = "high"
        if re.search(r"derecha|derechas|conservador|bloque conservador", text):
            metrics.append("right_bloc_pct")
            directions["right_bloc_pct"] = "high"
        if re.search(r"localista|voto local|partidos locales", text):
            metrics.append("local_vote_pct")
            directions["local_vote_pct"] = "high"
        if re.search(r"joven|jovenes|jóvenes", text):
            metrics.append("population_under_30")
            directions["population_under_30"] = "high"
        if party:
            metrics.append("vote_pct")
            directions["vote_pct"] = "high"
        return (metrics, directions, None) if len(metrics) >= 2 else (None, {}, None)

    def _correlation_metrics(self, text: str) -> list[str] | None:
        if not re.search(r"relacion|correlacion|correlaci[oó]n", text):
            return None
        metrics: list[str] = []
        if re.search(r"renta", text):
            metrics.append("income_individual")
        if re.search(r"abstencion|abstención", text):
            metrics.append("abstention_pct")
        if re.search(r"edad", text):
            metrics.append("average_age")
        if re.search(r"participacion|participación", text):
            metrics.append("participation_pct")
        return metrics[:2] if len(metrics) >= 2 else None


def _relative_metric_id(metric: str | None) -> str | None:
    return {
        "population_over_65": "population_over_65_pct",
        "population_under_30": "population_under_30_pct",
        "population_under_18": "population_under_18_pct",
        "votes": "vote_pct",
        "abstainers_count": "abstention_pct",
        "participation_count": "participation_pct",
    }.get(metric or "")
