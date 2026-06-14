from __future__ import annotations

from typing import Any

from app.ask.explainability.metric_explainer import MetricExplainer
from app.ask.explainability.schemas import ScoreExplanation


DEFAULT_RULES = [
    "0,80-1,00: combinación muy alta.",
    "0,60-0,79: combinación alta.",
    "0,40-0,59: combinación media.",
    "0,20-0,39: combinación baja.",
    "0,00-0,19: combinación muy baja.",
]


class ScoreExplainer:
    def __init__(self) -> None:
        self.metric_explainer = MetricExplainer()

    def explain(self, score_name: str | None, metadata: dict[str, Any] | None = None) -> ScoreExplanation | None:
        metadata = metadata or {}
        score_name = score_name or metadata.get("metric")
        if score_name not in {
            "composite_score",
            "cross_metric_score",
            "electoral_opportunity_score",
            "vulnerability_score",
            "growth_opportunity_score",
            "territorial_strength_score",
            "electoral_growth_opportunity",
            "mobilizable_abstention",
        }:
            if not score_name or "score" not in str(score_name):
                return None
        components = metadata.get("components") if isinstance(metadata.get("components"), list) else []
        variables = []
        for component in components:
            if isinstance(component, dict):
                metric = str(component.get("metric") or "")
                explanation = self.metric_explainer.explain(metric)
                variables.append(explanation.label if explanation else metric)
        label = self._score_label(score_name, variables)
        return ScoreExplanation(
            score_name=label,
            scale="0 a 1" if score_name in {"cross_metric_score", "composite_score", "mobilizable_abstention"} else "índice orientativo",
            plain_definition=(
                "El índice combinado es un índice normalizado de 0 a 1 que combina varias variables. "
                "Cuanto más cerca está de 1, más intensa es la combinación de factores analizados. "
                "No es un porcentaje ni una probabilidad: es una forma de ordenar secciones según varios criterios al mismo tiempo."
                if score_name in {"cross_metric_score", "composite_score", "mobilizable_abstention"}
                else "Es un índice orientativo para ordenar territorios según varios factores relevantes al mismo tiempo."
            ),
            variables_used=variables or (["Abstención", "Peso electoral", "Competitividad", "Afinidad territorial"] if score_name == "mobilizable_abstention" else []),
            interpretation_rules=DEFAULT_RULES if score_name in {"cross_metric_score", "composite_score", "mobilizable_abstention"} else [],
            caveat="No demuestra causalidad ni mide comportamientos individuales; es una lectura territorial por sección.",
        )

    def value_interpretation(self, value: Any) -> str | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric > 1:
            return None
        if numeric >= 0.8:
            label = "combinación muy alta"
        elif numeric >= 0.6:
            label = "combinación alta"
        elif numeric >= 0.4:
            label = "combinación media"
        elif numeric >= 0.2:
            label = "combinación baja"
        else:
            label = "combinación muy baja"
        return f"{str(round(numeric, 3)).replace('.', ',')} indica una {label}."

    def _score_label(self, score_name: str, variables: list[str]) -> str:
        if score_name == "cross_metric_score" and variables:
            return "Índice combinado de " + " y ".join(variable.lower() for variable in variables[:2])
        labels = {
            "electoral_opportunity_score": "Índice de oportunidad electoral",
            "electoral_growth_opportunity": "Índice de oportunidad electoral",
            "growth_opportunity_score": "Índice de oportunidad de crecimiento",
            "vulnerability_score": "Índice de vulnerabilidad",
            "territorial_strength_score": "Índice de fortaleza territorial",
            "mobilizable_abstention": "Índice de abstención movilizable",
        }
        return labels.get(score_name, "Índice combinado")
