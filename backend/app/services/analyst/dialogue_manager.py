from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal


DialogueAction = Literal[
    "answer_directly",
    "ask_clarification",
    "run_analysis",
    "explain_capabilities",
    "continue_previous_analysis",
]


@dataclass(frozen=True, slots=True)
class DetectedDialogueContext:
    domain: str = ""
    user_goal: str = ""
    target_audience: list[str] = field(default_factory=list)
    decision_type: str = ""
    known_constraints: list[str] = field(default_factory=list)
    missing_critical_context: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "user_goal": self.user_goal,
            "target_audience": self.target_audience,
            "decision_type": self.decision_type,
            "known_constraints": self.known_constraints,
            "missing_critical_context": self.missing_critical_context,
        }


@dataclass(frozen=True, slots=True)
class DialogueDecision:
    dialogue_action: DialogueAction
    reason: str
    detected_context: DetectedDialogueContext
    clarification_question: str | None = None
    analysis_brief: dict[str, Any] | None = None

    def model_dump(self) -> dict[str, Any]:
        return {
            "dialogue_action": self.dialogue_action,
            "reason": self.reason,
            "detected_context": self.detected_context.model_dump(),
            "clarification_question": self.clarification_question,
            "analysis_brief": self.analysis_brief,
        }


class ConsultativeDialogueManager:
    def decide(
        self,
        message: str,
        *,
        conversation_context: dict[str, Any] | None = None,
        active_layer: str | None = None,
    ) -> DialogueDecision:
        text = _normalize(message)
        context = conversation_context or {}

        if _is_conversational(text):
            return DialogueDecision(
                dialogue_action="explain_capabilities",
                reason="Conversational or greeting input; answer without data tools.",
                detected_context=DetectedDialogueContext(domain="conversation", user_goal="understand capabilities"),
            )

        if context and _is_contextual_follow_up(text):
            return DialogueDecision(
                dialogue_action="continue_previous_analysis",
                reason="The message refers to the previous turn or asks about data already used.",
                detected_context=DetectedDialogueContext(
                    domain=str(context.get("last_domain") or context.get("last_detected_domain") or ""),
                    user_goal=str(context.get("last_user_goal") or context.get("last_detected_intent") or ""),
                    decision_type="follow_up",
                ),
                analysis_brief={"active_layer": active_layer, "pending_clarification": context.get("pending_clarification")},
            )

        analytical_context = _direct_analytical_context(text)
        if analytical_context:
            return DialogueDecision(
                dialogue_action="run_analysis",
                reason="Direct factual metric question with a defined variable.",
                detected_context=analytical_context,
                analysis_brief={"strict_evidence": True, "active_layer": active_layer},
            )

        underspecified = _underspecified_strategic_context(text)
        if underspecified:
            return DialogueDecision(
                dialogue_action="ask_clarification",
                reason="Strategic decision is underspecified; ranking sections would be premature.",
                detected_context=underspecified,
                clarification_question=_clarification_for(underspecified),
            )

        strategic_context = _strategic_context(text)
        if strategic_context:
            return DialogueDecision(
                dialogue_action="run_analysis",
                reason="Strategic question contains enough context to choose a workflow.",
                detected_context=strategic_context,
                analysis_brief={"compare_hypotheses": True, "active_layer": active_layer},
            )

        return DialogueDecision(
            dialogue_action="ask_clarification",
            reason="The request does not define a clear SocTrace analysis goal.",
            detected_context=DetectedDialogueContext(
                domain="unknown",
                user_goal="unclear",
                decision_type="clarification",
                missing_critical_context=["analysis goal"],
            ),
            clarification_question=(
                "Podemos empezar por algo sencillo: población, edad, renta, voto, abstención, vivienda, "
                "crecimiento urbano o comunicación territorial. ¿Qué tema quieres explorar primero?"
            ),
        )


def _direct_analytical_context(text: str) -> DetectedDialogueContext | None:
    if re.search(r"mayor poblacion|mas poblacion|mas poblada|mas habitantes|mayor numero de habitantes", text):
        return DetectedDialogueContext(domain="demographic_analysis", user_goal="population maximum", decision_type="metric_lookup")
    if re.search(r"personas mayores|mayores de 65|mas mayores|poblacion mayor", text) and re.search(r"cual|donde|mas|mayor", text):
        return DetectedDialogueContext(domain="demographic_analysis", user_goal="elderly population maximum", decision_type="metric_lookup")
    if re.search(r"abstencion|participacion", text) and re.search(r"donde|mas alta|mayor|que seccion", text):
        return DetectedDialogueContext(domain="electoral_strategy", user_goal="turnout metric", decision_type="metric_lookup")
    if re.search(r"renta|ingreso", text) and re.search(r"donde|mas|mayor|que seccion", text):
        return DetectedDialogueContext(domain="demographic_analysis", user_goal="income metric", decision_type="metric_lookup")
    if re.search(r"20\d{2}.*20\d{2}", text) and re.search(r"cambiaron|cambio|variacion|evolucion", text):
        return DetectedDialogueContext(domain="analytical_change", user_goal="change between years", decision_type="metric_lookup")
    return None


def _underspecified_strategic_context(text: str) -> DetectedDialogueContext | None:
    if re.search(r"vivienda|comprar|comprarme|donde vivir|donde deberia comprar", text) and not re.search(
        r"para vivir|vivir|inversion|invertir|revalorizacion|revalorización|ninos|niños|familia", text
    ):
        return DetectedDialogueContext(
            domain="housing",
            user_goal="housing area advice",
            decision_type="strategic_location",
            missing_critical_context=["housing objective"],
        )
    if re.search(r"hablame de la vivienda|háblame de la vivienda|que zona es mejor|donde deberia invertir|dónde debería invertir", text):
        return DetectedDialogueContext(
            domain="housing" if "vivienda" in text else "territorial",
            user_goal="choose best area",
            decision_type="strategic_location",
            missing_critical_context=["decision objective"],
        )
    if re.search(r"accion local|acción local|iniciativa local", text):
        return DetectedDialogueContext(
            domain="territorial",
            user_goal="local action",
            decision_type="strategic_action",
            missing_critical_context=["action purpose"],
        )
    return None


def _strategic_context(text: str) -> DetectedDialogueContext | None:
    if re.search(r"curso|ingles|inglés|promocionar|promocionarme|captar", text):
        return DetectedDialogueContext(domain="territorial_marketing", user_goal="promote service", decision_type="territorial_activation")
    if re.search(r"formacion|formación|capacitar|edad laboral|empleo|desempleo|recualificacion|recualificación", text):
        return DetectedDialogueContext(domain="public_service", user_goal="labor training outreach", decision_type="public_outreach")
    if re.search(r"instalacion(?:es)? deportiva|equipamiento(?:s)? deportivo|deporte|deportiv", text):
        return DetectedDialogueContext(domain="sports_facilities_planning", user_goal="facility prioritization", decision_type="public_facility")
    if re.search(r"campana|campaña|pp|psoe|vox|candidato|presupuesto", text):
        return DetectedDialogueContext(domain="electoral_strategy", user_goal="campaign strategy", decision_type="political_strategy")
    return None


def _clarification_for(context: DetectedDialogueContext) -> str:
    if context.domain == "housing":
        return (
            "Puedo analizar vivienda desde tres enfoques: vivir, invertir o potencial de revalorización. "
            "¿Cuál es tu prioridad?"
        )
    if context.user_goal == "local action":
        return "¿La acción busca captar clientes, informar a vecinos, movilizar participación o prestar un servicio público?"
    return "Antes de ordenar secciones, dime qué objetivo quieres optimizar."


def _is_contextual_follow_up(text: str) -> bool:
    return bool(
        re.search(
            r"me gusta tu enfoque|y si|si tengo|tengo ninos|tengo niños|colegios|estas usando|estás usando|"
            r"estas considerando|estás considerando|capa socioeconomica|capa socioeconómica|afinalo|afínalo|"
            r"rehazlo|para familias|con renta|con niños|con ninos|que variables|qué variables|que herramientas|"
            r"qué herramientas|que datos|qué datos|de donde sale|de dónde sale",
            text,
        )
    )


def _is_conversational(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"(hola|buenas|buenos dias|buen dia|buenas tardes|buenas noches|gracias|muchas gracias|"
            r"vale|ok|okay|perfecto|de acuerdo|empezar|ayudame|ayuda|help|hey|hello|hi)",
            text,
        )
        or re.search(
            r"quien eres|que puedes hacer|dime preguntas|sugiereme preguntas|sugiere preguntas|"
            r"que preguntas|que puedo preguntarte|como me ayudas|como puedes ayudarme",
            text,
        )
    )


def _normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn"
    ).strip()
