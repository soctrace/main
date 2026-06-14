import re
from typing import Any

from app.ask.conversation import ConversationState
from app.services.local_analyst_service import normalize


REFERENCE_PATTERNS = {
    "sections": r"esas secciones|aquellas secciones|secciones anteriores|las anteriores|la anterior|las que mencionaste|esos barrios|la lista anterior|comp[aá]ralas|comparalas|esa seccion|esa sección|esa zona|en esa seccion|en esa sección|la seccion mas joven|la sección mas joven|la seccion más joven|la sección más joven",
    "age_range": r"esa cohorte|esas personas|ese grupo|ese rango|de esas personas",
    "result": r"ese resultado|los datos anteriores|esa consulta|los resultados previos|la consulta anterior|siempre ha sido|historicamente|históricamente",
}


def resolve_references(question: str, state: ConversationState | None) -> dict[str, Any]:
    text = normalize(question)
    resolved: dict[str, Any] = {}
    if state is None:
        return resolved

    implicit_section_metric = bool(re.search(r"\btienen\b|\btiene\b", text) and re.search(r"edad|renta|ingreso|perfil", text))
    if (re.search(REFERENCE_PATTERNS["sections"], text) or implicit_section_metric) and state.lastSections:
        resolved["resolvedSections"] = [section.model_dump() for section in state.lastSections]
    if re.search(REFERENCE_PATTERNS["sections"], text) and state.lastSection:
        resolved["resolvedSection"] = state.lastSection.model_dump()
    if re.search(REFERENCE_PATTERNS["age_range"], text) and state.lastAgeRange:
        resolved["resolvedAgeRange"] = state.lastAgeRange.model_dump()
    if re.search(REFERENCE_PATTERNS["result"], text) and state.lastResult is not None:
        resolved["resolvedLastResult"] = state.lastResult
    if state.lastResultType:
        resolved["lastResultType"] = state.lastResultType
    if state.lastMetric:
        resolved["lastMetric"] = state.lastMetric
    if state.lastDirection:
        resolved["lastDirection"] = state.lastDirection
    if state.lastYear:
        resolved["lastYear"] = state.lastYear
    if state.lastSection:
        resolved["lastSection"] = state.lastSection.model_dump()
    if state.lastParty:
        resolved["lastParty"] = state.lastParty
    if state.activeElection:
        resolved["activeElection"] = state.activeElection.model_dump()
    if state.municipality:
        resolved["municipality"] = state.municipality
    return resolved
