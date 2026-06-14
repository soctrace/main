from __future__ import annotations

from typing import Any

from app.ask.explainability.metric_explainer import MetricExplainer
from app.ask.explainability.schemas import MetricExplanation, ResponseExplanation, ScoreExplanation
from app.ask.explainability.score_explainer import ScoreExplainer


class ResponseExplainer:
    def __init__(self) -> None:
        self.metric_explainer = MetricExplainer()
        self.score_explainer = ScoreExplainer()

    def explain_tool_result(
        self,
        *,
        tool_name: str,
        operation: str,
        rows: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> tuple[ResponseExplanation | None, list[MetricExplanation], ScoreExplanation | None]:
        metrics = self._metrics_for_result(metadata)
        metric_explanations = self.metric_explainer.explain_many(metrics)
        score_explanation = self.score_explainer.explain(metadata.get("metric"), metadata)
        if tool_name == "cross_metric_ranking" or operation == "cross_metric_ranking":
            return self._cross_metric_response(rows, metric_explanations, score_explanation), metric_explanations, score_explanation
        if tool_name == "correlation_analysis":
            return self._correlation_response(metric_explanations), metric_explanations, score_explanation
        if tool_name in {"population_growth", "compare_years", "age_cohort_projection"}:
            return self._standard_response(metric_explanations, "El resultado ordena o estima territorios usando la métrica indicada."), metric_explanations, score_explanation
        if tool_name in {"electoral_viability_estimate", "electoral_growth_opportunity"}:
            return None, metric_explanations, score_explanation
        if metric_explanations:
            return self._standard_response(metric_explanations, "El resultado muestra las secciones más destacadas según la métrica consultada."), metric_explanations, score_explanation
        return None, [], score_explanation

    def _cross_metric_response(
        self,
        rows: list[dict[str, Any]],
        metric_explanations: list[MetricExplanation],
        score_explanation: ScoreExplanation | None,
    ) -> ResponseExplanation:
        variables = metric_explanations[:2]
        variable_text = " y ".join(variable.label.lower() for variable in variables) if variables else "los factores seleccionados"
        has_abstention = any(variable.metric == "abstention_pct" for variable in variables)
        has_left_vote = any(variable.metric == "left_bloc_pct" for variable in variables)
        score_text = score_explanation.plain_definition if score_explanation else "El índice combinado ordena secciones según varios factores al mismo tiempo."
        first = rows[0] if rows else {}
        first_reading = self.score_explainer.value_interpretation(first.get("value"))
        return ResponseExplanation(
            what_it_means=f"El resultado identifica las secciones donde coinciden con más intensidad {variable_text}.",
            how_it_is_calculated=(
                "Para cada variable se calcula una posición relativa de cada sección y después se combinan esos componentes en un único índice. "
                + score_text
            ),
            how_to_read_values=first_reading or "Cuanto más alto es el índice, más fuerte es la combinación territorial de los factores analizados.",
            practical_use=(
                "Estas zonas pueden ser especialmente relevantes para una estrategia de movilización: combinan voto progresista potencial y una bolsa de abstención que podría activarse."
                if has_abstention and has_left_vote
                else "Sirve para priorizar análisis territorial, movilización, intervención social o estrategia de campaña según los factores combinados."
            ),
            caveats=["No demuestra causalidad.", "No mide voto individual ni comportamiento individual; es una lectura territorial por sección."],
        )

    def _correlation_response(self, metric_explanations: list[MetricExplanation]) -> ResponseExplanation:
        labels = " y ".join(metric.label.lower() for metric in metric_explanations[:2]) or "las dos variables"
        return ResponseExplanation(
            what_it_means=f"El resultado mide si {labels} tienden a moverse juntas por sección.",
            how_it_is_calculated="Se calcula una correlación territorial entre los valores de ambas variables en las secciones disponibles.",
            how_to_read_values="Valores cercanos a 1 indican asociación positiva; cercanos a -1, asociación negativa; cerca de 0, relación débil o inexistente.",
            practical_use="Sirve para detectar patrones territoriales que merecen análisis posterior.",
            caveats=["Correlación no implica causalidad.", "Es una lectura ecológica por sección, no individual."],
        )

    def _standard_response(self, metric_explanations: list[MetricExplanation], meaning: str) -> ResponseExplanation:
        metric = metric_explanations[0]
        caveats = [metric.caveat] if metric.caveat else []
        return ResponseExplanation(
            what_it_means=meaning,
            how_it_is_calculated=f"Se ordenan las secciones usando {metric.label.lower()}: {metric.plain_definition}",
            how_to_read_values=metric.interpretation,
            practical_use="Sirve para comparar zonas y priorizar dónde mirar con más detalle.",
            caveats=caveats,
        )

    def _metrics_for_result(self, metadata: dict[str, Any]) -> list[str]:
        components = metadata.get("components") if isinstance(metadata.get("components"), list) else []
        metrics = [
            str(component.get("metric"))
            for component in components
            if isinstance(component, dict) and component.get("metric")
        ]
        for key in ("metric", "x_metric", "y_metric"):
            value = metadata.get(key)
            if value and value not in metrics and value not in {"cross_metric_score", "correlation"}:
                metrics.append(str(value))
        return metrics
