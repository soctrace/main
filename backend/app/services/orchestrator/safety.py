from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


def normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def is_greeting(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.fullmatch(r"(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|ola)[!. ]*", normalized))


def is_suggestion_request(text: str) -> bool:
    normalized = normalize_text(text)
    return "no se que preguntar" in normalized or bool(
        re.search(r"\b(que puedo preguntarte|sugiere(me)? preguntas|dame preguntas)\b", normalized)
    )


def is_conversational_or_open_ended(text: str) -> bool:
    normalized = normalize_text(text)
    if is_greeting(text) or is_suggestion_request(text):
        return True
    if bool(re.search(r"\b(tienes capacidad de conversar|puedes conversar|que puedes hacer|como funcionas|explicame como funcionas)\b", normalized)):
        return True
    if bool(re.search(r"\b(hablame|cuentame|explicame|dime algo)\b.*\b(renta|vivienda|poblacion|voto|crecimiento urbano|soctrace)\b", normalized)):
        return True
    return False


def is_housing_ambiguous(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.fullmatch(r".*\b(hablame|dime|cuentame)\b.*\b(vivienda|inmobiliari[oa])\b.*", normalized))


def asks_previous_layers(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.search(r"\b(usando|usaste|utilizaste|datos|variables|fuentes|capas)\b.*\b(inteligencia|capa|variables|datos|fuentes|usado)\b", normalized))


def asks_same_sections_challenge(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.search(r"\b(por que|porque)\b.*\b(siempre|mismas|mismos)\b.*\b(secciones|zonas)\b", normalized))


def asks_concept_distinction(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.search(r"\b(crecimiento urbano|potencial de voto|potencial electoral|residencial|voto)\b.*\b(o|versus|vs|diferencia)\b", normalized))


def asks_budget_campaign_without_party(text: str) -> bool:
    normalized = normalize_text(text)
    has_budget = bool(re.search(r"\b(5000|5\.000|presupuesto|invertir|euros)\b", normalized))
    has_campaign = bool(re.search(r"\b(campana electoral|campaña electoral|campana|campaña)\b", normalized))
    has_party = bool(re.search(r"\b(pp|psoe|vox|por andalucia|ciudadanos)\b", normalized))
    return has_budget and has_campaign and not has_party


def asks_individual_vote_by_address(text: str) -> bool:
    normalized = normalize_text(text)
    has_address = bool(re.search(r"\b(vivo|calle|avenida|avda|direccion|vecinos)\b", normalized))
    has_vote = bool(re.search(r"\b(votan|vota|voto|votos|elecciones|partido)\b", normalized))
    return has_address and has_vote


def asks_school_context(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(re.search(r"\b(colegio|colegios|escuela|guarderia|ninos pequenos|niños pequeños)\b", normalized))


def infer_topic(text: str) -> str:
    normalized = normalize_text(text)
    if re.search(r"\b(joven|jovenes|mayores|edad|ninos|niños)\b", normalized):
        return "age_structure"
    if re.search(r"\b(renta|ingreso|socioeconom)\b", normalized):
        return "income"
    if re.search(r"\b(vivienda|inmobiliari|revalorizacion|invertir)\b", normalized):
        return "housing"
    if re.search(r"\b(voto|votan|partido|eleccion|abstencion)\b", normalized):
        return "electoral"
    if re.search(r"\b(poblacion|habitantes)\b", normalized):
        return "population"
    return "conversation"


def infer_goal_concept(text: str) -> str:
    normalized = normalize_text(text)
    if re.search(r"\b(crecer|crecimiento|potencial|campana|campaña|voto|partido|pp|psoe|vox)\b", normalized):
        return "electoral_growth_potential"
    if re.search(r"\b(formacion|edad laboral|servicio|colegio|familias|vulnerabilidad)\b", normalized):
        return "public_service_need"
    if re.search(r"\b(comercial|tienda|negocio|cliente|demanda)\b", normalized):
        return "commercial_opportunity"
    if re.search(r"\b(urbano|residencial|vivienda|revalorizacion|edific)\b", normalized):
        return "urban_expansion"
    return "direct_data_lookup"


@dataclass(frozen=True, slots=True)
class GroundingValidation:
    ok: bool
    warnings: list[str]


def validate_grounded_answer(answer: str, rows: list[dict[str, Any]], variables_used: list[str]) -> GroundingValidation:
    warnings: list[str] = []
    if not rows:
        if re.search(r"\d", answer):
            warnings.append("La respuesta contenía cifras, pero ninguna tool devolvió filas.")
        return GroundingValidation(ok=not warnings, warnings=warnings)

    allowed_numbers = _numbers_from_rows(rows)
    answer_numbers = _numbers_from_text(answer)
    invented_numbers = [number for number in answer_numbers if number not in allowed_numbers]
    if invented_numbers:
        warnings.append("La síntesis del LLM contenía cifras no devueltas por las tools.")

    section_names = [
        normalize_text(str(row.get("section_name")))
        for row in rows
        if row.get("section_name")
    ]
    section_mentions = re.findall(r"seccion\s+\d+\s*[·.-]?\s*[\w ]*", normalize_text(answer))
    if section_mentions and section_names:
        unknown_mentions = [
            mention
            for mention in section_mentions
            if not any(mention.strip() in section_name or section_name in mention.strip() for section_name in section_names)
        ]
        if unknown_mentions:
            warnings.append("La síntesis del LLM mencionaba una sección no presente en los resultados.")

    if "inteligencia socioeconomica" in normalize_text(answer) and not any("socioeconomic" in variable.lower() or "income" in variable.lower() for variable in variables_used):
        warnings.append("La respuesta atribuía Inteligencia Socioeconómica sin variables compatibles.")

    return GroundingValidation(ok=not warnings, warnings=warnings)


def _numbers_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    numbers: set[str] = set()
    for row in rows:
        for value in row.values():
            if isinstance(value, (int, float)):
                numbers.update(_numbers_from_text(str(value)))
            elif isinstance(value, str):
                numbers.update(_numbers_from_text(value))
    return numbers


def _numbers_from_text(text: str) -> set[str]:
    return {match.lstrip("0") or "0" for match in re.findall(r"\d+(?:[.,]\d+)?", text)}
