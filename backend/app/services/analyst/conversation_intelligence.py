from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationIntelligence:
    conversation_type: str
    requires_data: bool
    requires_strict_evidence: bool
    should_answer_without_tools: bool
    user_intent: str
    suggested_response_mode: str

    def model_dump(self) -> dict[str, object]:
        return {
            "conversation_type": self.conversation_type,
            "requires_data": self.requires_data,
            "requires_strict_evidence": self.requires_strict_evidence,
            "should_answer_without_tools": self.should_answer_without_tools,
            "user_intent": self.user_intent,
            "suggested_response_mode": self.suggested_response_mode,
        }


class ConversationIntelligenceLayer:
    def classify(self, message: str) -> ConversationIntelligence:
        text = _normalize(message)
        if _is_conversational_message(text):
            return ConversationIntelligence(
                conversation_type="conversational",
                requires_data=False,
                requires_strict_evidence=False,
                should_answer_without_tools=True,
                user_intent="greeting_or_conversational",
                suggested_response_mode="conversational",
            )
        if re.search(
            r"dime que preguntas puedo hacerte|dime qué preguntas puedo hacerte|"
            r"sugiereme preguntas|sugi[eé]reme preguntas|sugiere preguntas|"
            r"que puedo preguntarte|qué puedo preguntarte|"
            r"que puedes hacer|qué puedes hacer|como puedes ayudarme|cómo puedes ayudarme|"
            r"que tipo de analisis|qué tipo de análisis|que tipo de analisis haces|qué tipo de análisis haces|"
            r"explicame como funciona|explícame cómo funciona|explicame como funciona ask soctrace|explícame cómo funciona ask soctrace|"
            r"ask soctrace|ayuda$|help$",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="conversational",
                requires_data=False,
                requires_strict_evidence=False,
                should_answer_without_tools=True,
                user_intent="capabilities_or_suggested_questions",
                suggested_response_mode="conversational",
            )
        if re.search(
            r"estas considerando|est[áa]s considerando|estas teniendo en cuenta|est[áa]s teniendo en cuenta|"
            r"lo (?:estas|est[áa]s) usando|lo tomas en cuenta|has usado|de donde sale|de dónde sale|"
            r"que datos estas usando|qué datos estás usando|que variables has usado|qué variables has usado|"
            r"por que esas secciones|por qué esas secciones|incluye la capa|incluye inteligencia socioeconomica|"
            r"incluye inteligencia socioeconómica|tenemos en cuenta desempleo|rehazlo usando|afina el analisis|"
            r"afina el análisis|no me convence|explicalo mejor|explícalo mejor",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="follow_up",
                requires_data=False,
                requires_strict_evidence=False,
                should_answer_without_tools=True,
                user_intent="contextual_follow_up",
                suggested_response_mode="contextual",
            )
        if _is_population_max_question(text):
            return ConversationIntelligence(
                conversation_type="analytical",
                requires_data=True,
                requires_strict_evidence=True,
                should_answer_without_tools=False,
                user_intent="population_max_section",
                suggested_response_mode="analytical",
            )
        if _is_elderly_population_max_question(text):
            return ConversationIntelligence(
                conversation_type="analytical",
                requires_data=True,
                requires_strict_evidence=True,
                should_answer_without_tools=False,
                user_intent="elderly_population_max_section",
                suggested_response_mode="analytical",
            )
        if _is_change_between_years_question(text):
            return ConversationIntelligence(
                conversation_type="analytical",
                requires_data=True,
                requires_strict_evidence=True,
                should_answer_without_tools=False,
                user_intent="change_between_years",
                suggested_response_mode="analytical",
            )
        if re.search(
            r"formacion|formación|capacitacion|capacitación|edad laboral|insercion laboral|inserción laboral|"
            r"orientacion profesional|orientación profesional|empleo|desempleo|desemplead|productividad|"
            r"tejido productivo|ocupacion|ocupación|actividad economica|actividad económica|sectores|"
            r"ramas de actividad|competencias|cursos profesionales|recualificacion|recualificación",
            text,
        ) and not re.search(r"\bayudas?\b|subvencion|subvención", text):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="labor_training_outreach",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"instalacion(?:es)? deportiva|equipamiento(?:s)? deportivo|polideportivo|pista(?:s)? deportiva|"
            r"cancha(?:s)?|deporte|deportiv",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="public_facility_prioritization",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"comprar(?:me)? una vivienda|comprar vivienda|comprar casa|comprarme una casa|"
            r"zona para vivir|donde vivir|donde comprar|invertir en vivienda|vivienda|inmobiliari|residencial",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="housing_area_recommendation",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"servicio publico|campana informativa|campaña informativa|ayuntamiento|vecinos|"
            r"participacion ciudadana|participación ciudadana|difusion municipal|difusión municipal|programa publico|"
            r"\bayudas?\b|subvencion|subvención|desemplead|paro|oficina de empleo|servicios sociales|comunicacion publica|comunicación pública",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="public_service_outreach",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"promocionar|promocionarme|promocion|promoción|captar alumnos|captar clientes|dar a conocer|"
            r"publicitar|difundir|lanzar un curso|curso gratuito|clases de ingles|clases de inglés|academia|"
            r"servicio local|negocio local|campana comercial|campaña comercial|marketing local|abrir un negocio|"
            r"lanzar un servicio|ofertar un curso|nuevo servicio|poner en marcha|captar usuarios|clientes|"
            r"consumidores|farmacia|inmobiliaria|comercio|publicidad|promote|marketing|launch a course|"
            r"free course|english course|local business|target customers|where should i promote|where should i advertise",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="territorial_marketing",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"familias|jovenes|jóvenes|mayores|ninos|niños|estudiantes|adolescentes|"
            r"poblacion extranjera|población extranjera|renta|edad|perfil demografico|perfil demográfico",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="demographic_targeting",
                suggested_response_mode="territorial_consultant",
            )
        if re.search(
            r"campana|campaña|estrategia|invertir|presupuesto|recursos|candidato|visitar|"
            r"repartir|mensaje|moviliz|persuasi|crecer|growth|campaign",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="strategic",
                requires_data=True,
                requires_strict_evidence=False,
                should_answer_without_tools=False,
                user_intent="political_strategy",
                suggested_response_mode="executive",
            )
        if re.search(
            r"donde|dónde|cual|cu[aá]l|cuanto|cu[aá]nto|mas alta|más alta|mas poblada|"
            r"gan[oó]|abstencion|abstención|joven|renta|voto|resultado",
            text,
        ):
            return ConversationIntelligence(
                conversation_type="analytical",
                requires_data=True,
                requires_strict_evidence=True,
                should_answer_without_tools=False,
                user_intent="evidence_question",
                suggested_response_mode="analytical",
            )
        return ConversationIntelligence(
            conversation_type="diagnostic",
            requires_data=True,
            requires_strict_evidence=True,
            should_answer_without_tools=False,
            user_intent="general_political_analysis",
            suggested_response_mode="standard",
        )


def conversational_answer(message: str) -> tuple[str, list[str]]:
    text = _normalize(message)
    if _is_greeting_like(text):
        return (
            "Hola. Soy Ask soctrace, tu analista territorial para Mijas. Puedes preguntarme por población, edad, renta, comportamiento electoral, vivienda, crecimiento urbano o estrategias de comunicación territorial.",
            [
                "¿Cuál es la sección con mayor población?",
                "¿Dónde es más alta la abstención?",
                "Dime qué preguntas puedo hacerte",
            ],
        )
    if re.search(r"gracias|vale|ok|okay|perfecto|de acuerdo", text):
        return (
            "Perfecto. Cuando quieras, dime qué quieres analizar de Mijas y lo aterrizo con los datos disponibles.",
            [
                "¿Cuál es la sección con mayor población?",
                "¿Qué secciones cambiaron más entre 2019 y 2023?",
                "¿Dónde hay más personas mayores?",
            ],
        )
    if "preguntas" in text or "preguntarte" in text:
        return (
            "Claro. Puedes preguntarme cosas en cinco grandes bloques:\n\n"
            "1. Estrategia electoral\n"
            "- ¿Dónde puede crecer el PP en Mijas?\n"
            "- ¿Qué secciones debería visitar primero un candidato?\n"
            "- ¿Dónde es más alta la abstención?\n\n"
            "2. Inteligencia territorial\n"
            "- ¿Qué zonas han crecido más?\n"
            "- ¿Dónde hay más población joven?\n"
            "- ¿Qué secciones combinan densidad y crecimiento?\n\n"
            "3. Servicios públicos\n"
            "- ¿Dónde tendría más impacto una instalación deportiva?\n"
            "- ¿Dónde debería concentrar una campaña de ayudas a desempleados?\n\n"
            "4. Vivienda y urbanismo\n"
            "- ¿Qué zonas tienen mayor presión residencial?\n"
            "- ¿Dónde analizarías una compra de vivienda?\n\n"
            "5. Comunicación local\n"
            "- ¿Dónde promocionarías un curso, servicio o campaña informativa?",
            [
                "¿Dónde puede crecer el PP en Mijas?",
                "¿Qué secciones debería visitar primero el candidato?",
                "¿Dónde concentraría 5.000 euros de campaña?",
            ],
        )
    return (
        "Soy SocTrace Political Analyst: puedo ayudarte a convertir datos territoriales, demográficos, socioeconómicos y electorales en decisiones políticas. "
        "Puedo priorizar secciones, detectar abstención movilizable, comparar zonas, proponer agenda del candidato, repartir presupuesto de campaña y adaptar mensajes por territorio.\n\n"
        "Lo importante: no soy solo un buscador de datos. Mi trabajo es darte una decisión política útil, explicar la evidencia que la sostiene y señalar la limitación cuando haga falta.",
        [
            "¿Dónde es más alta la abstención?",
            "¿Qué secciones debería visitar primero el candidato?",
            "¿Cómo invertirías 5.000 euros para el PP?",
        ],
    )


def _normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn"
    )


def _is_conversational_message(text: str) -> bool:
    return bool(
        _is_greeting_like(text)
        or re.fullmatch(r"(gracias|muchas gracias|vale|ok|okay|perfecto|de acuerdo|empezar|ayudame|ayuda|help)", text)
        or re.search(r"quien eres|quién eres|que puedes hacer|qué puedes hacer|dime preguntas|ayudame|ayúdame", text)
    )


def _is_greeting_like(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"(hola|buenas|buenos dias|buen dia|buenas tardes|buenas noches|hey|hello|hi)",
            text,
        )
    )


def _is_population_max_question(text: str) -> bool:
    return bool(
        re.search(
            r"mayor poblacion|mas poblacion|mas poblada|mayor numero de habitantes|"
            r"mas habitantes|seccion con mayor poblacion|seccion electoral mas poblada",
            text,
        )
    )


def _is_elderly_population_max_question(text: str) -> bool:
    has_metric_shape = re.search(r"cual|que seccion|donde hay|mayor numero|mas", text)
    has_elderly_term = re.search(r"personas mayores|mayores de 65|mas mayores|poblacion mayor|mayores", text)
    has_strategy_term = re.search(r"promocion|promocionar|campana|servicio|captar|difundir|marketing|curso", text)
    return bool(has_metric_shape and has_elderly_term and not has_strategy_term)


def _is_change_between_years_question(text: str) -> bool:
    return bool(
        re.search(r"20\d{2}.*20\d{2}", text)
        and re.search(r"cambiaron mas|cambio mas|variacion|evolucion|cambiaron|cambio", text)
    )
