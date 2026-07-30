from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.analyst.executive_reasoning import ExecutiveReasoning
from app.services.analyst.planner import PoliticalPlan
from app.services.analyst.schemas import AnalystSection, AnalystTable, StrategicRecommendation
from app.services.analyst.tools import AnalystToolResult


STRATEGIC_INTENTS = {
    "campaign_plan",
    "candidate_visit_plan",
    "abstention_analysis",
    "party_growth_opportunity",
    "mobilization_strategy",
    "persuasion_strategy",
    "territorial_prioritization",
    "territorial_marketing",
    "service_launch",
    "commercial_targeting",
    "demographic_targeting",
    "public_service_outreach",
    "labor_training_outreach",
    "sports_facilities_planning",
    "real_estate_location_advice",
    "urban_planning",
    "socioeconomic_analysis",
    "general_territorial_advice",
}

TERRITORIAL_INTENTS = {
    "territorial_marketing",
    "service_launch",
    "commercial_targeting",
    "demographic_targeting",
    "public_service_outreach",
    "labor_training_outreach",
    "sports_facilities_planning",
    "real_estate_location_advice",
    "urban_planning",
    "socioeconomic_analysis",
    "general_territorial_advice",
}

LABEL_TRANSLATIONS = {
    "Residential Growth Area": "zona de crecimiento residencial",
    "Mobilization Opportunity": "oportunidad de movilizacion",
    "Persuasion Opportunity": "oportunidad de persuasion",
    "Conservative Stronghold": "zona fuerte para el bloque conservador",
    "Progressive Stronghold": "zona fuerte para el bloque progresista",
    "Swing Section": "seccion disputada",
    "Low Electoral ROI Area": "baja rentabilidad electoral",
    "High Abstention Area": "abstencion relevante",
    "Aging Population Area": "poblacion envejecida",
    "Young Population Area": "poblacion joven",
    "High Income Area": "renta alta",
    "Low Income Area": "renta baja",
    "Door-to-Door Priority": "prioridad de puerta a puerta",
    "Digital Campaign Priority": "prioridad digital",
}


@dataclass(slots=True)
class ComposedAnalystAnswer:
    answer: str
    tables: list[AnalystTable]
    recommendations: list[StrategicRecommendation]
    follow_up_questions: list[str]
    warnings: list[str]
    priority_sections: list[dict[str, Any]]
    evidence_table: list[dict[str, Any]]
    limitations: list[str]


def should_compose(intent: str) -> bool:
    return intent in STRATEGIC_INTENTS


def compose_final_answer(
    *,
    message: str,
    intent: str,
    plan: PoliticalPlan | None,
    tool_result: AnalystToolResult,
    sections: list[AnalystSection],
    executive_reasoning: ExecutiveReasoning | None = None,
) -> ComposedAnalystAnswer:
    top_sections = _dedupe_sections(sections)[:5]
    rows_by_id = {str(row.get("section_id")): row for row in tool_result.rows if row.get("section_id")}
    budget = _extract_budget(message)
    party = plan.target_party if plan and plan.target_party else _extract_party(message)
    guarded_backstop = intent == "general_territorial_advice" and _looks_like_unsafe_general_territorial_input(message)
    if intent == "sports_facilities_planning":
        answer = _sports_facilities_answer(top_sections, rows_by_id)
    elif intent == "real_estate_location_advice":
        answer = _real_estate_answer(top_sections, rows_by_id)
    elif intent == "public_service_outreach":
        answer = _public_service_answer(top_sections, rows_by_id)
    elif intent == "labor_training_outreach":
        answer = _labor_training_answer(top_sections, rows_by_id)
    elif intent in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice"}:
        answer = _general_territorial_answer(top_sections, rows_by_id, message)
    elif intent in TERRITORIAL_INTENTS:
        answer = _territorial_answer(top_sections, rows_by_id, plan)
    elif intent == "abstention_analysis":
        answer = _abstention_answer(top_sections, rows_by_id, executive_reasoning)
    elif intent == "candidate_visit_plan":
        answer = _candidate_visit_answer(top_sections, rows_by_id, party, executive_reasoning)
    elif intent == "party_growth_opportunity":
        answer = _growth_answer(top_sections, rows_by_id, party, executive_reasoning)
    else:
        answer = _campaign_answer(top_sections, rows_by_id, party, budget, executive_reasoning)
    compact_tables = _territorial_tables(top_sections, rows_by_id, intent) if intent in TERRITORIAL_INTENTS else _compact_tables(top_sections, rows_by_id, party)
    return ComposedAnalystAnswer(
        answer=answer,
        tables=compact_tables,
        recommendations=_territorial_recommendations(top_sections, rows_by_id, intent) if intent in TERRITORIAL_INTENTS else _recommendations(top_sections, rows_by_id),
        follow_up_questions=_analytical_follow_ups() if guarded_backstop else _follow_ups(intent),
        warnings=[_domain_caveat(intent)],
        priority_sections=_priority_sections(top_sections, rows_by_id),
        evidence_table=_table_dicts(compact_tables),
        limitations=(executive_reasoning.limitations if executive_reasoning else ["Priorizacion operativa basada en datos internos disponibles."]),
    )


def _territorial_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    plan: PoliticalPlan | None,
) -> str:
    service = _service_label(plan.target_service if plan else None)
    audience = _audience_label(plan.target_audience) if plan and plan.target_audience else "familias, jóvenes, residentes cercanos y usuarios potenciales"
    section_lines = _territorial_section_lines(sections, rows_by_id)
    channels = _dedupe_text([
        str(rows_by_id.get(section.section_id, {}).get("recommended_channel") or "")
        for section in sections[:5]
    ])
    channel_lines = "\n".join(f"• {channel}" for channel in channels[:4]) or "• Comercios locales, asociaciones vecinales y anuncios geolocalizados."
    action_lines = "\n".join(
        f"• {section.name}: {rows_by_id.get(section.section_id, {}).get('recommended_action') or 'activar promoción local con mensaje simple y formulario de contacto.'}"
        for section in sections[:5]
    ) or "• Empezar con una prueba piloto en 3-5 zonas y medir respuesta por canal."
    return (
        f"Sí. Para {service} no intentaría promocionarlo por todo Mijas de forma homogénea. "
        "Lo enfocaría en zonas con familias, población joven, crecimiento residencial y buena capacidad de difusión comunitaria.\n\n"
        "1. Decisión territorial\n"
        f"Mi prioridad sería empezar por las secciones con mejor combinación de demanda probable y facilidad de activación local. Público objetivo: {audience}.\n\n"
        "2. Territorios donde empezaría\n"
        f"{section_lines}\n\n"
        "3. Canales de comunicación\n"
        f"{channel_lines}\n\n"
        "4. Cómo lo haría\n"
        f"{action_lines}\n\n"
        "5. Mensaje recomendado\n"
        "Usaría un mensaje muy directo: plaza gratuita, beneficio claro, nivel inicial sin barreras y reserva sencilla por WhatsApp. "
        "Para familias, enfatizaría apoyo escolar y oportunidad de futuro; para jóvenes/adultos, empleabilidad y conversación práctica.\n\n"
        "6. Qué evitaría\n"
        "No gastaría esfuerzo en una difusión genérica por todo el municipio ni en anuncios sin segmentación territorial. Primero probaría 3-5 zonas, mediría contactos reales y después ampliaría.\n\n"
        "7. Cautela breve\n"
        "SocTrace no expone todavía todos los indicadores ideales para educación u origen extranjero en esta herramienta; por eso la recomendación usa proxies de edad, crecimiento, densidad, renta y entorno residencial."
    )


def _sports_facilities_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
) -> str:
    section_lines = _territorial_section_lines(sections, rows_by_id)
    criteria = _dedupe_text([
        str(rows_by_id.get(section.section_id, {}).get("recommended_channel") or "")
        for section in sections[:5]
    ])
    criteria_lines = "\n".join(f"• {item}" for item in criteria[:4]) or "• Contrastar población joven, densidad, accesibilidad peatonal y suelo disponible."
    action_lines = "\n".join(
        f"• {section.name}: {rows_by_id.get(section.section_id, {}).get('recommended_action') or 'evaluar una instalación deportiva de proximidad.'}"
        for section in sections[:5]
    ) or "• Empezar con un diagnóstico de demanda y accesibilidad antes de decidir la inversión."
    return (
        "Sí. Para decidir dónde hacen falta instalaciones deportivas en Mijas no usaría una lógica de promoción, sino de necesidad territorial y accesibilidad.\n\n"
        "1. Decisión territorial\n"
        "Priorizaría zonas donde coincidan población joven, densidad, crecimiento residencial y presión urbana. Ahí una pista multideporte o equipamiento de proximidad puede tener más uso social.\n\n"
        "2. Zonas donde empezaría el análisis\n"
        f"{section_lines}\n\n"
        "3. Criterios de validación\n"
        f"{criteria_lines}\n\n"
        "4. Qué haría\n"
        f"{action_lines}\n\n"
        "5. Qué evitaría\n"
        "No lo plantearía como una campaña de captación ni como una acción de marketing. Tampoco decidiría solo por población total: comprobaría distancia a equipamientos existentes, disponibilidad de suelo y demanda vecinal.\n\n"
        "6. Cautela breve\n"
        "La herramienta aporta proxies demográficos y urbanos; para cerrar una inversión pública haría falta cruzarlo con inventario real de instalaciones, suelo municipal y mantenimiento."
    )


def _real_estate_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
) -> str:
    section_lines = _territorial_section_lines(sections, rows_by_id)
    criteria = _dedupe_text([
        str(rows_by_id.get(section.section_id, {}).get("recommended_channel") or "")
        for section in sections[:5]
    ])
    criteria_lines = "\n".join(f"• {item}" for item in criteria[:4]) or "• Comparar servicios, movilidad, renta del entorno, densidad y trayectoria residencial."
    action_lines = "\n".join(
        f"• {section.name}: {rows_by_id.get(section.section_id, {}).get('recommended_action') or 'comparar vivienda concreta con servicios, movilidad y precio.'}"
        for section in sections[:5]
    ) or "• Evaluar vivienda concreta antes de decidir, no solo la sección."
    return (
        "Sí, pero lo separaría en dos decisiones: zona para vivir y comprar vivienda concreta. SocTrace puede ayudarte con la primera; la segunda requiere revisar precio, estado, ruido, comunidad y financiación.\n\n"
        "1. Decisión territorial\n"
        "Miraría zonas con crecimiento residencial, servicios cercanos, renta compatible, densidad razonable y señales de consolidación urbana. Para inversión, además valoraría liquidez y posible revalorización.\n\n"
        "2. Zonas que analizaría primero\n"
        f"{section_lines}\n\n"
        "3. Criterios de compra\n"
        f"{criteria_lines}\n\n"
        "4. Cómo lo haría\n"
        f"{action_lines}\n\n"
        "5. Qué evitaría\n"
        "No compraría solo porque una zona salga arriba en un ranking territorial. Usaría el ranking para acotar visitas y después compararía precio por metro, estado de la finca, transporte, ruido y servicios.\n\n"
        "6. Cautela breve\n"
        "Esto no es asesoramiento financiero ni tasación. Es una priorización territorial basada en datos internos disponibles."
    )


def _public_service_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
) -> str:
    section_lines = _territorial_section_lines(sections, rows_by_id)
    channels = _dedupe_text([
        str(rows_by_id.get(section.section_id, {}).get("recommended_channel") or "")
        for section in sections[:5]
    ])
    channel_lines = "\n".join(f"• {channel}" for channel in channels[:4]) or (
        "• Servicios sociales, centros municipales, asociaciones vecinales, oficinas de empleo y comercios de proximidad."
    )
    action_lines = "\n".join(
        f"• {section.name}: {rows_by_id.get(section.section_id, {}).get('recommended_action') or 'concentrar comunicación pública clara con apoyo municipal y comunitario.'}"
        for section in sections[:5]
    ) or "• Hacer una primera oleada informativa y medir solicitudes o consultas reales por zona."
    return (
        "Sí. Para una campaña sobre ayudas a personas desempleadas, no la plantearía como una promoción comercial, sino como una acción de comunicación pública. "
        "Priorizaría zonas donde puedan coincidir vulnerabilidad socioeconómica, necesidad de información y facilidad de contacto comunitario.\n\n"
        "1. Decisión territorial\n"
        "Empezaría por las secciones con señales de demanda probable y buena capacidad de difusión local.\n\n"
        "2. Zonas donde concentraría la primera oleada\n"
        f"{section_lines}\n\n"
        "3. Canales recomendados\n"
        f"{channel_lines}\n\n"
        "4. Cómo lo haría\n"
        f"{action_lines}\n\n"
        "5. Qué evitaría\n"
        "No usaría lenguaje de oferta comercial ni de captación de clientes. El mensaje debería explicar requisitos, plazos, documentación y punto de atención.\n\n"
        "6. Cautela breve\n"
        "La priorización usa indicadores socioeconómicos y territoriales disponibles; no sustituye a los registros administrativos reales de demandantes."
    )


def _labor_training_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
) -> str:
    section_lines = _territorial_section_lines(sections, rows_by_id)
    channels = _dedupe_text([
        str(rows_by_id.get(section.section_id, {}).get("recommended_channel") or "")
        for section in sections[:5]
    ])
    channel_lines = "\n".join(f"• {channel}" for channel in channels[:4]) or (
        "• Servicios de empleo, orientación, centros municipales, asociaciones vecinales y colaboración con empresas locales."
    )
    action_lines = "\n".join(
        f"• {section.name}: {rows_by_id.get(section.section_id, {}).get('recommended_action') or 'intensificar difusión con servicios de empleo y tejido local.'}"
        for section in sections[:5]
    ) or "• Reforzar la comunicación en zonas con necesidad de recualificación y potencial laboral."
    return (
        "Sí. Para una formación dirigida a personas en edad laboral no priorizaría simplemente las zonas más jóvenes. "
        "Miraría dónde coinciden tres factores: volumen de población activa potencial, necesidad u oportunidad socioeconómica y facilidad de activación territorial.\n\n"
        "1. Hipótesis de trabajo\n"
        "Compararía tres enfoques antes de decidir: zonas con más población activa potencial, zonas con mayor necesidad de recualificación y zonas con mejor potencial productivo para responder a la formación.\n\n"
        "2. Decisión territorial\n"
        "Con los datos de SocTrace, priorizaría secciones donde la Inteligencia Socioeconómica apunte a potencial productivo, perfil laboral, ocupación y ramas de actividad, vulnerabilidad, renta y oportunidad de empleabilidad.\n\n"
        "3. Zonas donde intensificaría la promoción\n"
        f"{section_lines}\n\n"
        "4. Canales recomendados\n"
        f"{channel_lines}\n\n"
        "5. Cómo lo haría\n"
        f"{action_lines}\n\n"
        "6. Qué evitaría\n"
        "No usaría una plantilla infantil o familiar. El mensaje debe centrarse en empleabilidad, mejora de competencias, horarios compatibles y salida profesional.\n\n"
        "7. Cautela breve\n"
        "La priorización usa Inteligencia Socioeconómica y proxies territoriales; no sustituye registros administrativos individuales de empleo o demanda formativa."
    )


def _general_territorial_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    message: str = "",
) -> str:
    if _looks_like_unsafe_general_territorial_input(message):
        return (
            "Esta pregunta no define una priorización territorial general. "
            "Necesito que concretes si quieres analizar población, edad, renta, voto, abstención, vivienda o crecimiento urbano."
        )
    section_lines = _territorial_section_lines(sections, rows_by_id)
    return (
        "Sí. Para una decisión territorial general en Mijas empezaría con pocas zonas y una hipótesis clara, no con una recomendación genérica para todo el municipio.\n\n"
        "1. Zonas a revisar primero\n"
        f"{section_lines}\n\n"
        "2. Método\n"
        "Cruzo población, edad, crecimiento, densidad, renta y entorno urbano. Después validaría en campo qué problema real hay que resolver y qué recursos existen cerca.\n\n"
        "3. Cautela breve\n"
        "Cuando la pregunta no define objetivo concreto, la salida debe leerse como primera priorización territorial, no como decisión final."
    )


def _territorial_section_lines(sections: list[AnalystSection], rows_by_id: dict[str, dict[str, Any]]) -> str:
    if not sections:
        return "• Empezaría con zonas residenciales densas y con población joven, validando la respuesta con una prueba piloto."
    lines: list[str] = []
    for index, section in enumerate(sections[:5], start=1):
        row = rows_by_id.get(section.section_id, {})
        reason = row.get("target_audience_reason") or _why_it_matters(section, row)
        lines.append(f"{index}. {section.name}: {reason}")
    return "\n".join(lines)


def _looks_like_analytical_metric_question(message: str) -> bool:
    text = _normalize(message)
    return bool(
        re.search(
            r"cual es|que seccion|donde hay mas|donde hay menos|que secciones cambiaron|"
            r"mayor poblacion|personas mayores|mas joven|mas renta|mas abstencion",
            text,
        )
    )


def _looks_like_unsafe_general_territorial_input(message: str) -> bool:
    text = _normalize(message).strip()
    if not text:
        return True
    if _looks_like_short_or_conversational_input(text):
        return True
    return _looks_like_analytical_metric_question(message)


def _looks_like_short_or_conversational_input(text: str) -> bool:
    if len(text.split()) <= 2 and not re.search(r"accion local|iniciativa local|prioriza|priorizar|territorio|territorial|zona|zonas", text):
        return True
    return bool(
        re.fullmatch(
            r"(hola|buenas|buenos dias|buen dia|buenas tardes|buenas noches|gracias|muchas gracias|"
            r"vale|ok|okay|perfecto|de acuerdo|empezar|ayudame|ayuda|help|hey|hello|hi)",
            text,
        )
        or re.search(r"quien eres|que puedes hacer|dime preguntas|ayudame", text)
    )


def _service_label(service: str | None) -> str:
    if not service:
        return "la iniciativa local"
    if service == "free English course":
        return "un curso gratuito de inglés"
    if service == "English course":
        return "un curso de inglés"
    if service == "academia":
        return "una academia"
    return service


def _audience_label(audience: list[str]) -> str:
    translations = {
        "families": "familias",
        "students": "estudiantes",
        "young adults": "jóvenes adultos",
        "foreign residents": "residentes extranjeros",
        "older residents": "personas mayores",
    }
    return ", ".join(translations.get(item, item) for item in audience)


def _campaign_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    party: str | None,
    budget: int | None,
    executive_reasoning: ExecutiveReasoning | None,
) -> str:
    party_label = party or "la candidatura"
    budget_label = _money(budget) if budget else "un presupuesto limitado"
    section_lines = _section_lines(sections[:5], rows_by_id)
    first_names = ", ".join(section.name for section in sections[:4]) or "las secciones con mayor retorno operativo"
    allocation = _budget_allocation(budget)
    if budget:
        allocation_lines = "\n".join(f"• {_money(amount)}: {label}. {why}" for label, amount, why in allocation)
        allocation_heading = f"4. Cómo repartiría {budget_label}"
    else:
        allocation_lines = (
            "• Primero, presencia territorial y puerta a puerta en las zonas de mayor retorno.\n"
            "• Después, agenda local del candidato en secciones disputadas.\n"
            "• Como refuerzo, publicidad digital hiperlocal y material impreso solo donde haya prioridad territorial.\n"
            "• En el cierre, recordatorio de voto y seguimiento de contactos."
        )
        allocation_heading = "4. Cómo repartiría los recursos"
    actions = "\n".join(
        f"• {section.name}: {_recommended_action(rows_by_id.get(section.section_id, {}))}"
        for section in sections[:5]
    )
    if not actions:
        actions = "• Concentraria el trabajo en pocas zonas, con presencia repetida y mensajes adaptados."

    thesis = (
        executive_reasoning.executive_thesis
        if executive_reasoning
        else f"Sí. Para {party_label} no intentaría cubrir todo Mijas; concentraría el esfuerzo en pocas secciones con alta repetición."
    )
    diagnosis = (
        executive_reasoning.political_reading
        if executive_reasoning
        else "La campaña debe separar movilización, persuasión y retención según el tipo de oportunidad territorial."
    )
    decision = (
        executive_reasoning.strategic_decision
        if executive_reasoning
        else f"Mi decisión sería concentrar el esfuerzo en {first_names}."
    )
    not_to_do = executive_reasoning.what_not_to_do if executive_reasoning else [
        "No gastaría el presupuesto en una campaña genérica para todo el municipio.",
        "No invertiría en anuncios digitales sin aterrizaje territorial.",
        "No haría actos grandes que consuman dinero sin generar contactos identificables.",
    ]
    not_to_do_lines = "\n".join(f"• {item}" for item in not_to_do)
    return (
        f"{thesis} Haría una campana quirurgica: pocas secciones, mucha repetición y mensajes adaptados.\n\n"
        "1. Recomendación ejecutiva\n"
        f"{decision} Con {budget_label}, el objetivo no sería hacer ruido en todo Mijas, sino ganar presencia donde cada euro pueda producir más contacto político útil.\n\n"
        "2. Diagnóstico estratégico\n"
        f"{diagnosis}\n\n"
        "3. Territorios prioritarios\n"
        f"{section_lines}\n\n"
        f"{allocation_heading}\n"
        f"{allocation_lines}\n\n"
        "5. Acciones por zona\n"
        f"{actions}\n\n"
        "6. Mensaje político recomendado\n"
        f"Para {party_label}, usaria un mensaje de proximidad y gestion: seguridad cotidiana, servicios municipales visibles, limpieza, movilidad y escucha vecinal. "
        "En zonas de movilizacion, el tono debe ser practico: resolver problemas y recordar la importancia de votar. En zonas de persuasion, menos ideologia abstracta y mas credibilidad local: candidato presente, compromisos verificables y comparacion clara de gestion.\n\n"
        "7. Qué no haría\n"
        f"{not_to_do_lines}\n\n"
        "8. Cautela breve\n"
        "Esta recomendacion no es una encuesta ni una prediccion cerrada; es una priorizacion operativa basada en los datos internos disponibles."
    )


def _candidate_visit_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    party: str | None,
    executive_reasoning: ExecutiveReasoning | None,
) -> str:
    party_label = party or "la candidatura"
    section_lines = _section_lines(sections[:5], rows_by_id)
    return (
        f"{executive_reasoning.executive_thesis if executive_reasoning else 'Si tuviera que ordenar la agenda del candidato, empezaria por pocas visitas bien preparadas, no por una gira dispersa.'} "
        f"Para {party_label}, priorizaria estas zonas:\n\n"
        f"{section_lines}\n\n"
        "La visita debe tener formato de contacto directo: paseo corto, reunion vecinal pequena, escucha de demandas y cierre con una peticion concreta. "
        "El valor politico esta en convertir presencia en relacion: nombres, telefonos, problemas localizados y recordatorio de voto.\n\n"
        "Cautela metodologica\n"
        "Esta recomendacion ordena prioridades con datos internos disponibles; conviene validarla con conocimiento local antes de cerrar la agenda."
    )


def _abstention_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    executive_reasoning: ExecutiveReasoning | None,
) -> str:
    section_lines = _section_lines(sections[:5], rows_by_id)
    first = sections[0] if sections else None
    first_row = rows_by_id.get(first.section_id, {}) if first else {}
    first_value = _pct(first_row.get("abstention_rate_pct") or (first.metrics.get("abstention_rate_pct") if first else None))
    direct = (
        f"La abstención más alta del ranking aparece en {first.name}"
        + (f", con {first_value}" if first_value else "")
        + "."
        if first
        else "No tengo una sección concreta suficiente para ordenar la abstención sin inventar datos."
    )
    return (
        f"{direct}\n\n"
        "1. Evidencia\n"
        f"{section_lines}\n\n"
        "2. Metodología\n"
        "Ordeno las secciones por abstención observada y uso la tabla territorial para interpretar dónde hay mayor oportunidad de activación.\n\n"
        "3. Acción recomendada\n"
        "En estas zonas haria puerta a puerta, llamadas, mensajes de recordatorio y presencia en calle con problemas muy concretos del barrio. "
        "La clave es reducir friccion: que el votante sepa por que votar, cuando votar y que la candidatura esta presente.\n\n"
        "4. Cautela breve\n"
        "La abstencion observada senala oportunidad de movilizacion, pero no garantiza conversion automatica en votos."
    )


def _growth_answer(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    party: str | None,
    executive_reasoning: ExecutiveReasoning | None,
) -> str:
    party_label = party or "el partido objetivo"
    section_lines = _section_lines(sections[:5], rows_by_id)
    return (
        f"{executive_reasoning.executive_thesis if executive_reasoning else f'Para {party_label}, buscaria crecimiento con una mezcla de movilizacion, persuasion y retencion.'} "
        "No todas las secciones sirven para lo mismo: algunas piden calle, otras mensaje y otras defensa de base.\n\n"
        "1. Donde puede crecer primero\n"
        f"{section_lines}\n\n"
        "2. Como trabajaria el crecimiento\n"
        "Donde haya abstencion relevante, pondria equipo de movilizacion. Donde el margen sea estrecho, pondria candidato y mensaje comparativo. "
        "Donde la base ya sea favorable, no gastaria demasiado en persuadir: reforzaria fidelidad y participacion.\n\n"
        "3. Cautela metodologica\n"
        "Esto no sustituye una encuesta; convierte datos territoriales disponibles en una hoja de ruta operativa."
    )


def _section_lines(sections: list[AnalystSection], rows_by_id: dict[str, dict[str, Any]]) -> str:
    if not sections:
        return "• No hay suficiente evidencia seccional para ordenar zonas sin inventar datos."
    lines: list[str] = []
    for index, section in enumerate(sections, start=1):
        row = rows_by_id.get(section.section_id, {})
        lines.append(f"{index}. {section.name}: {_why_it_matters(section, row)}")
    return "\n".join(lines)


def _why_it_matters(section: AnalystSection, row: dict[str, Any]) -> str:
    reasons: list[str] = []
    label = _resolved_label(row)
    if label:
        reasons.append(_label_sentence(label))
    abstention = _number(row.get("abstention_rate_pct") or section.metrics.get("abstention_rate_pct"))
    margin = _number(row.get("victory_margin_pct") or section.metrics.get("victory_margin_pct"))
    growth = _number(row.get("population_growth_pct") or section.metrics.get("population_growth_pct"))
    target = _number(row.get("target_party_vote_pct") or section.metrics.get("target_party_vote_pct"))
    if growth is not None and growth >= 3:
        reasons.append("senales de crecimiento residencial")
    if abstention is not None:
        reasons.append(f"abstencion del {abstention:.1f}%")
    if margin is not None:
        reasons.append(f"margen de {margin:.1f} puntos")
    if target is not None:
        reasons.append(f"voto objetivo del {target:.1f}%")
    translated_tags = _translate_tags(section.tags)
    if translated_tags:
        reasons.extend(translated_tags[:2])
    if reasons:
        return "interesa porque combina " + ", ".join(_dedupe_text(reasons)) + "."
    return "interesa porque combina oportunidad de expansion, margen operativo y potencial de activacion territorial."


def _label_sentence(label: str) -> str:
    return {
        "movilizacion": "oportunidad de movilizacion",
        "persuasion": "oportunidad de persuasion",
        "retencion": "prioridad de retencion",
        "expansion": "oportunidad de expansion",
        "visita prioritaria": "valor alto para presencia del candidato",
    }.get(label, label)


def _recommended_action(row: dict[str, Any]) -> str:
    label = _resolved_label(row)
    if label == "movilizacion":
        return "puerta a puerta, recordatorio de voto y presencia de calle con mensajes muy concretos."
    if label == "persuasion":
        return "visita del candidato, reunion pequena y mensaje comparativo sobre gestion municipal."
    if label == "retencion":
        return "reforzar base, apoderados, interventores y comunicaciones de fidelizacion."
    if label == "expansion":
        return "testar mensaje local, pequena campana digital geolocalizada y escucha vecinal."
    return "combinar presencia fisica, mensaje local y seguimiento de contactos."


def _campaign_objective(row: dict[str, Any]) -> str:
    label = _resolved_label(row)
    return {
        "movilizacion": "Movilizar abstencion",
        "persuasion": "Persuadir voto competitivo",
        "retencion": "Retener base propia",
        "expansion": "Abrir crecimiento",
        "visita prioritaria": "Generar presencia",
    }.get(label, "Priorizar contacto")


def _resolved_label(row: dict[str, Any]) -> str:
    explicit = str(row.get("strategic_label") or "").strip().lower()
    if explicit:
        return explicit
    abstention = _number(row.get("abstention_rate_pct"))
    margin = _number(row.get("victory_margin_pct"))
    winning_party = str(row.get("winning_party") or "").upper()
    target = _number(row.get("target_party_vote_pct"))
    winning = _number(row.get("winning_party_pct"))
    if abstention is not None and abstention >= 45:
        return "movilizacion"
    if margin is not None and margin <= 5:
        return "persuasion"
    if winning_party and target is not None and winning is not None and target >= winning - 2:
        return "retencion"
    return "expansion"


def _compact_tables(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    party: str | None,
) -> list[AnalystTable]:
    if not sections:
        return []
    base_columns = ["Prioridad", "Seccion", "Por que importa", "Accion", "Objetivo"]
    optional = [
        ("Abstencion", "abstention_rate_pct", _pct),
        (f"{party or 'Partido'}", "target_party_vote_pct", _pct),
        ("Margen", "victory_margin_pct", _pct),
        ("Poblacion", "population_total", lambda value: str(value) if value is not None else ""),
        ("Score", "opportunity_score", lambda value: f"{_number(value):.1f}" if _number(value) is not None else ""),
    ]
    visible_optional = [
        item for item in optional if _populated_count([rows_by_id.get(section.section_id, {}) for section in sections], item[1]) >= max(1, len(sections) // 2)
    ]
    columns = base_columns + [item[0] for item in visible_optional]
    rows: list[list[str]] = []
    for index, section in enumerate(sections[:5], start=1):
        row = rows_by_id.get(section.section_id, {})
        values = [
            str(index),
            section.name,
            _why_it_matters(section, row),
            _recommended_action(row),
            _campaign_objective(row),
        ]
        values.extend(formatter(row.get(key) or section.metrics.get(key)) for _, key, formatter in visible_optional)
        rows.append(values)
    return [AnalystTable(title="Prioridades de campana", columns=columns, rows=rows)]


def _territorial_tables(
    sections: list[AnalystSection],
    rows_by_id: dict[str, dict[str, Any]],
    intent: str = "territorial_marketing",
) -> list[AnalystTable]:
    if not sections:
        return []
    if intent == "sports_facilities_planning":
        title = "Prioridades para instalaciones deportivas"
        columns = ["Prioridad", "Seccion", "Por que priorizar", "Criterio", "Accion", "Score"]
    elif intent == "real_estate_location_advice":
        title = "Zonas residenciales a analizar"
        columns = ["Prioridad", "Seccion", "Por que analizar", "Criterio", "Accion", "Score"]
    else:
        title = "Prioridades territoriales"
        columns = ["Prioridad", "Seccion", "Por que encaja", "Canal", "Accion", "Score"]
    rows: list[list[str]] = []
    for index, section in enumerate(sections[:5], start=1):
        row = rows_by_id.get(section.section_id, {})
        rows.append(
            [
                str(index),
                section.name,
                str(row.get("target_audience_reason") or _why_it_matters(section, row)),
                str(row.get("recommended_channel") or ""),
                str(row.get("recommended_action") or ""),
                f"{_number(row.get('score') or row.get('opportunity_score')):.1f}" if _number(row.get("score") or row.get("opportunity_score")) is not None else "",
            ]
        )
    return [AnalystTable(title=title, columns=columns, rows=rows)]


def _priority_sections(sections: list[AnalystSection], rows_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "priority": index,
            "section_id": section.section_id,
            "section_name": section.name,
            "reason": _why_it_matters(section, rows_by_id.get(section.section_id, {})),
            "recommended_action": _recommended_action(rows_by_id.get(section.section_id, {})),
            "campaign_objective": _campaign_objective(rows_by_id.get(section.section_id, {})),
        }
        for index, section in enumerate(sections[:5], start=1)
    ]


def _table_dicts(tables: list[AnalystTable]) -> list[dict[str, str]]:
    if not tables:
        return []
    table = tables[0]
    return [
        {column: row[index] if index < len(row) else "" for index, column in enumerate(table.columns)}
        for row in table.rows
    ]


def _recommendations(sections: list[AnalystSection], rows_by_id: dict[str, dict[str, Any]]) -> list[StrategicRecommendation]:
    recommendations: list[StrategicRecommendation] = []
    for section in sections[:3]:
        row = rows_by_id.get(section.section_id, {})
        recommendations.append(
            StrategicRecommendation(
                priority="high" if (_number(section.score) or 0) >= 70 else "medium",
                section_id=section.section_id,
                title=f"Priorizar {section.name}",
                rationale=_why_it_matters(section, row),
                actions=[_recommended_action(row)],
            )
        )
    return recommendations


def _territorial_recommendations(sections: list[AnalystSection], rows_by_id: dict[str, dict[str, Any]], intent: str = "territorial_marketing") -> list[StrategicRecommendation]:
    recommendations: list[StrategicRecommendation] = []
    for section in sections[:3]:
        row = rows_by_id.get(section.section_id, {})
        if intent == "sports_facilities_planning":
            title = f"Priorizar estudio deportivo en {section.name}"
            default_action = "Evaluar demanda, accesibilidad y suelo para equipamiento deportivo de proximidad."
            default_rationale = "Zona con señales territoriales útiles para priorizar instalaciones deportivas."
        elif intent == "real_estate_location_advice":
            title = f"Analizar compra en {section.name}"
            default_action = "Comparar vivienda concreta con precio, servicios, movilidad y calidad urbana."
            default_rationale = "Zona con señales residenciales útiles para acotar búsqueda de vivienda."
        elif intent == "public_service_outreach":
            title = f"Concentrar comunicación pública en {section.name}"
            default_action = "Activar servicios sociales, centros municipales, oficinas de empleo y asociaciones vecinales."
            default_rationale = "Zona con señales territoriales útiles para una campaña informativa pública."
        elif intent == "labor_training_outreach":
            title = f"Intensificar formación laboral en {section.name}"
            default_action = "Coordinar servicios de empleo, centros municipales, asociaciones y empresas locales."
            default_rationale = "Zona con señales de potencial productivo, empleabilidad o necesidad de recualificación."
        elif intent in {"urban_planning", "socioeconomic_analysis", "general_territorial_advice", "demographic_targeting"}:
            title = f"Analizar {section.name}"
            default_action = "Validar indicadores territoriales y condiciones reales de la zona."
            default_rationale = "Zona con señales territoriales útiles para análisis operativo."
        else:
            title = f"Promocionar en {section.name}"
            default_action = "Activar promoción local con canal de contacto sencillo."
            default_rationale = "Zona con señales territoriales útiles para captación local."
        recommendations.append(
            StrategicRecommendation(
                priority="high" if (_number(row.get("score") or section.score) or 0) >= 50 else "medium",
                section_id=section.section_id,
                title=title,
                rationale=str(row.get("target_audience_reason") or default_rationale),
                actions=[str(row.get("recommended_action") or default_action)],
            )
        )
    return recommendations


def _budget_allocation(budget: int | None) -> list[tuple[str, int, str]]:
    total = budget or 5000
    items = [
        ("puerta a puerta, presencia en calle y agenda local del candidato", 0.30, "Es donde un presupuesto pequeno genera mas contacto politico real"),
        ("publicidad digital hiperlocal", 0.24, "Sirve para repetir mensaje solo en las zonas priorizadas"),
        ("material impreso por seccion", 0.18, "Debe apoyar la presencia fisica, no sustituirla"),
        ("reuniones vecinales pequenas", 0.14, "Aumentan credibilidad y permiten escuchar demandas concretas"),
        ("operacion de recordatorio de voto", 0.10, "Convierte simpatia en participacion efectiva"),
        ("seguimiento y ajuste", 0.04, "Permite mover dinero si una zona no responde"),
    ]
    allocated = [(label, int(round(total * share / 50) * 50), why) for label, share, why in items]
    delta = total - sum(amount for _, amount, _ in allocated)
    if allocated:
        label, amount, why = allocated[-1]
        allocated[-1] = (label, amount + delta, why)
    return allocated


def _follow_ups(intent: str) -> list[str]:
    if intent == "candidate_visit_plan":
        return [
            "¿Quieres que convierta esto en una agenda semanal del candidato?",
            "¿Quieres mensajes por seccion?",
            "¿Quieres un plan de puerta a puerta?",
        ]
    if intent == "abstention_analysis":
        return [
            "¿Quieres una operacion de movilizacion por seccion?",
            "¿Quieres priorizar jovenes, mayores o renta?",
            "¿Quieres mensajes de recordatorio de voto?",
        ]
    if intent == "sports_facilities_planning":
        return [
            "¿Quieres diferenciar instalaciones para jóvenes, mayores o deporte federado?",
            "¿Quieres que lo cruce con accesibilidad y equipamientos existentes?",
            "¿Quieres convertirlo en una propuesta municipal por fases?",
        ]
    if intent == "real_estate_location_advice":
        return [
            "¿Quieres priorizar vivir, invertir o buscar revalorización?",
            "¿Quieres comparar dos zonas concretas?",
            "¿Quieres una checklist para visitar viviendas?",
        ]
    if intent == "public_service_outreach":
        return [
            "¿Quieres adaptar el mensaje para servicios sociales y oficinas de empleo?",
            "¿Quieres priorizar cartelería, atención presencial o campaña geolocalizada sobria?",
            "¿Quieres convertirlo en un plan de comunicación pública por fases?",
        ]
    if intent == "labor_training_outreach":
        return [
            "¿Quieres que separe perfiles de empleabilidad y recualificación?",
            "¿Quieres adaptar canales para servicios de empleo y empresas locales?",
            "¿Quieres ver qué variables socioeconómicas han pesado más?",
        ]
    if intent in TERRITORIAL_INTENTS:
        return [
            "¿Quieres que lo convierta en un plan de promoción de 2 semanas?",
            "¿Quieres mensajes por zona y canal?",
            "¿Quieres priorizar familias, jóvenes o población extranjera?",
        ]
    return [
        "¿Quieres que convierta esto en una agenda semanal del candidato?",
        "¿Quieres que lo adapte a PP, PSOE, Vox o una candidatura local?",
        "¿Quieres que prepare mensajes por seccion?",
    ]


def _analytical_follow_ups() -> list[str]:
    return [
        "¿Quieres ver el ranking completo de secciones?",
        "¿Quieres comparar esta sección con la media municipal?",
        "¿Quieres cruzarlo con renta, edad o voto?",
    ]


def _dedupe_sections(sections: list[AnalystSection]) -> list[AnalystSection]:
    seen: set[str] = set()
    output: list[AnalystSection] = []
    for section in sections:
        if section.section_id in seen:
            continue
        seen.add(section.section_id)
        section.tags[:] = _dedupe_text(section.tags)
        output.append(section)
    return output


def _domain_caveat(intent: str) -> str:
    if intent == "sports_facilities_planning":
        return "La priorización orienta dónde estudiar demanda; antes de invertir habría que comprobar suelo disponible, equipamientos existentes y uso real."
    if intent == "real_estate_location_advice":
        return "La recomendación no sustituye una tasación ni una visita concreta de vivienda; sirve para acotar zonas de análisis."
    if intent == "public_service_outreach":
        return "La priorización usa indicadores socioeconómicos y territoriales disponibles; no sustituye a los registros administrativos reales de demandantes."
    if intent == "labor_training_outreach":
        return "La priorización usa Inteligencia Socioeconómica y proxies territoriales; no sustituye registros administrativos individuales de empleo o demanda formativa."
    if intent in {"territorial_marketing", "service_launch", "commercial_targeting"}:
        return "Faltan indicadores directos de demanda educativa u origen; se usan proxies demográficos y territoriales."
    return "La priorización usa indicadores territoriales disponibles y debe contrastarse con información operativa específica."


def _translate_tags(tags: list[str]) -> list[str]:
    return _dedupe_text([LABEL_TRANSLATIONS.get(tag, "") for tag in tags if LABEL_TRANSLATIONS.get(tag)])


def _dedupe_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = _normalize(value)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _populated_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is not None and row.get(key) != "")


def _extract_budget(message: str) -> int | None:
    text = _normalize(message).replace(".", "").replace(",", "")
    match = re.search(r"(\d{3,7})\s*(?:eur|euros?|€)", text)
    if not match:
        match = re.search(r"(?:invertir|presupuesto|gastar)\s+(\d{3,7})", text)
    if not match:
        return None
    return int(match.group(1))


def _extract_party(message: str) -> str | None:
    text = _normalize(message)
    for party in ["PP", "PSOE", "VOX"]:
        if re.search(rf"(^|[^a-z0-9]){party.lower()}([^a-z0-9]|$)", text):
            return party
    return None


def _money(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value:,.0f} euros".replace(",", ".")


def _pct(value: Any) -> str:
    number = _number(value)
    return "" if number is None else f"{number:.1f}%"


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn"
    )
