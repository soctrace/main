from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


POLITICAL_GOALS = {
    "campaign_plan",
    "candidate_visit_plan",
    "territorial_prioritization",
    "party_growth_opportunity",
    "abstention_analysis",
    "mobilization_strategy",
    "persuasion_strategy",
    "electoral_diagnosis",
    "section_profile",
    "comparison",
    "general_political_advice",
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
    "population_max_section",
    "elderly_population_max_section",
    "population_change_between_years",
    "electoral_change_between_years",
    "income_change_between_years",
    "ambiguous_change_between_years",
    "unknown_or_conversational",
}


@dataclass(slots=True)
class PoliticalPlan:
    goal: str
    domain: str
    target_party: str | None
    municipality_id: str
    target_service: str | None = None
    target_audience: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    reasoning_tasks: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    start_year: int | None = None
    end_year: int | None = None

    def model_dump(self) -> dict[str, object]:
        return {
            "goal": self.goal,
            "domain": self.domain,
            "target_party": self.target_party,
            "target_service": self.target_service,
            "target_audience": self.target_audience,
            "municipality_id": self.municipality_id,
            "required_tools": self.required_tools,
            "reasoning_tasks": self.reasoning_tasks,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "start_year": self.start_year,
            "end_year": self.end_year,
        }


class PoliticalPlanner:
    def plan(self, message: str, municipality_id: str) -> PoliticalPlan:
        text = _normalize(message)
        target_party = _extract_party(text)
        normalized_municipality = _municipality_id(municipality_id, text)
        goal = self._goal(text)
        domain = _domain(goal)
        clarification = _clarification_question(goal, text)
        years = _years(text)
        return PoliticalPlan(
            goal=goal,
            domain=domain,
            target_party=target_party,
            target_service=_target_service(text),
            target_audience=_target_audience(text),
            municipality_id=normalized_municipality,
            required_tools=_required_tools(goal),
            reasoning_tasks=_reasoning_tasks(goal, target_party),
            needs_clarification=clarification is not None,
            clarification_question=clarification,
            start_year=years[0] if len(years) >= 2 else None,
            end_year=years[1] if len(years) >= 2 else None,
        )

    def _goal(self, text: str) -> str:
        if _is_conversational_message(text):
            return "unknown_or_conversational"
        if re.search(r"d\s*['’]?\s*hondt|concejal|escano|reparto", text):
            return "electoral_diagnosis"
        if _is_population_max_question(text):
            return "population_max_section"
        if _is_elderly_population_max_question(text):
            return "elderly_population_max_section"
        if _is_change_between_years_question(text):
            if re.search(r"poblacion|población|habitantes|demograf", text):
                return "population_change_between_years"
            if re.search(r"voto|electoral|eleccion|elecciones|abstencion|participacion|pp|psoe|vox", text):
                return "electoral_change_between_years"
            if re.search(r"renta|ingreso|income", text):
                return "income_change_between_years"
            return "ambiguous_change_between_years"
        if re.search(r"compar|versus| vs | frente a ", text):
            return "comparison"
        if re.search(r"seccion\s+\d+|29\d{8}|perfil\s+de\s+seccion|perfil\s+seccional", text):
            return "section_profile"
        if re.search(r"abstencion|participacion", text):
            return "abstention_analysis"
        if re.search(r"formacion|formación|capacitacion|capacitación|edad laboral|insercion laboral|inserción laboral|orientacion profesional|orientación profesional|empleo|desempleo|desemplead|productividad|tejido productivo|ocupacion|ocupación|actividad economica|actividad económica|sectores|ramas de actividad|competencias|cursos profesionales|recualificacion|recualificación", text) and not re.search(r"\bayudas?\b|subvencion|subvención", text):
            return "labor_training_outreach"
        if re.search(r"instalacion(?:es)? deportiva|equipamiento(?:s)? deportivo|polideportivo|pista(?:s)? deportiva|cancha(?:s)?|deporte|deportiv", text):
            return "sports_facilities_planning"
        if re.search(r"comprar(?:me)? una vivienda|comprar vivienda|comprar casa|comprarme una casa|zona para vivir|donde vivir|donde comprar|invertir en vivienda|vivienda|inmobiliari|residencial", text):
            return "real_estate_location_advice"
        if re.search(r"urbanismo|planeamiento|equipamiento urbano|crecimiento urbano|presion urbana|presión urbana|infraestructura", text):
            return "urban_planning"
        if re.search(r"socioeconom|renta|desigualdad|vulnerabilidad|nivel economico|nivel económico", text):
            return "socioeconomic_analysis"
        if re.search(r"servicio publico|campana informativa|ayuntamiento|vecinos|participacion ciudadana|difusion municipal|programa publico|\bayudas?\b|subvencion|subvención|desemplead|paro|oficina de empleo|servicios sociales|comunicacion publica|comunicación pública", text):
            return "public_service_outreach"
        if re.search(r"familias|jovenes|jóvenes|mayores|ninos|niños|estudiantes|adolescentes|poblacion extranjera|perfil demografico|perfil demográfico", text):
            return "demographic_targeting"
        if re.search(r"abrir un negocio|lanzar un servicio|ofertar un curso|nuevo servicio|poner en marcha|captar usuarios|lanzar un curso|curso gratuito|clases de ingles|clases de inglés|english course|free course|launch a course", text):
            return "service_launch"
        if re.search(r"promocionar|promocionarme|promocion|promoción|captar alumnos|captar clientes|dar a conocer|publicitar|difundir|academia|servicio local|negocio local|campana comercial|campaña comercial|marketing local|promote|marketing|local business|target customers|where should i promote|where should i advertise", text):
            return "territorial_marketing"
        if re.search(r"clientes|consumidores|negocio|venta|farmacia|inmobiliaria|comercio|publicidad", text):
            return "commercial_targeting"
        if re.search(
            r"campana|campaña|estrategia electoral|organizar.*electoral|plan de campana|plan de campaña|"
            r"where should we start the campaign|help me organize an electoral campaign|"
            r"que deberia hacer un candidato|qué debería hacer un candidato|como organizarias la campana|"
            r"cómo organizarías la campaña|disena una estrategia|diseña una estrategia",
            text,
        ):
            return "campaign_plan"
        if re.search(r"visitar|visita|candidate visit|recorrido|agenda|puerta a puerta", text):
            return "candidate_visit_plan"
        if re.search(r"puede crecer|crecer|grow|growth|oportunidad|swing|partido popular|psoe|vox|ciudadanos|\bpp\b", text):
            return "party_growth_opportunity"
        if re.search(r"moviliz|movilizacion|turnout|get out the vote|gotv", text):
            return "mobilization_strategy"
        if re.search(r"persuasi|persuasion|convencer|indecis", text):
            return "persuasion_strategy"
        if re.search(r"diagnostico|diagnóstico|resultado|eleccion|elecciones|voto|ganador", text):
            return "electoral_diagnosis"
        if re.search(r"accion local|acción local|iniciativa local|lugar|zona|barrio|territorio|mijas", text):
            return "general_territorial_advice"
        return "unknown_or_conversational"


def _required_tools(goal: str) -> list[str]:
    if goal == "unknown_or_conversational":
        return []
    if goal == "population_max_section":
        return ["get_population_ranking"]
    if goal == "elderly_population_max_section":
        return ["get_age_structure"]
    if goal == "population_change_between_years":
        return ["get_population_change_ranking"]
    if goal == "electoral_change_between_years":
        return ["get_electoral_change_ranking"]
    if goal == "income_change_between_years":
        return ["get_income_change_ranking"]
    if goal == "campaign_plan":
        return [
            "get_election_results",
            "get_turnout_analysis",
            "get_population_trend",
            "get_age_structure",
            "get_income_profile",
            "rank_sections_by_opportunity",
            "build_campaign_recommendation",
        ]
    if goal == "candidate_visit_plan":
        return ["rank_sections_by_opportunity", "build_campaign_recommendation"]
    if goal == "abstention_analysis":
        return ["get_turnout_analysis", "rank_sections_by_opportunity"]
    if goal == "party_growth_opportunity":
        return ["get_election_results", "rank_sections_by_opportunity", "build_campaign_recommendation"]
    if goal in {"mobilization_strategy", "persuasion_strategy", "territorial_prioritization"}:
        return ["get_turnout_analysis", "rank_sections_by_opportunity", "get_population_trend", "get_age_structure"]
    if goal in _TERRITORIAL_DATA_GOALS:
        return [
            "get_age_structure",
            "get_population_trend",
            "get_income_profile",
            "get_population_density",
            "get_socioeconomic_profile",
            "get_land_built_profile",
        ]
    return []


def _reasoning_tasks(goal: str, target_party: str | None) -> list[str]:
    tasks = ["separar datos observados, interpretacion y recomendacion"]
    if goal == "unknown_or_conversational":
        return ["pedir aclaracion sin ejecutar ranking territorial"]
    if goal in {
        "population_max_section",
        "elderly_population_max_section",
        "population_change_between_years",
        "electoral_change_between_years",
        "income_change_between_years",
    }:
        tasks.extend(["resolver métrica directa", "responder con valor observado", "evitar plantilla estratégica"])
        return tasks
    if goal == "campaign_plan":
        tasks.extend(["diagnostico territorial", "prioridades de movilizacion", "prioridades de persuasion", "fases de campana"])
    if goal == "candidate_visit_plan":
        tasks.extend(["ordenar visitas", "justificar valor politico por seccion"])
    if goal == "abstention_analysis":
        tasks.extend(["comparar abstencion seccional", "recomendar movilizacion"])
    if goal == "party_growth_opportunity":
        tasks.extend(["detectar tipo de crecimiento", "proponer mensaje local"])
    if goal in _TERRITORIAL_DATA_GOALS:
        tasks.extend([
            "identify likely demand territories",
            "identify target audiences or beneficiaries",
            "prioritize channels or operational criteria",
            "recommend domain-specific territorial actions",
        ])
    if goal == "sports_facilities_planning":
        tasks.extend(["prioritize public facility need", "avoid commercial promotion framing"])
    if goal == "real_estate_location_advice":
        tasks.extend(["compare residential suitability", "avoid course or campaign framing"])
    if target_party is None and _domain(goal) == "electoral_strategy":
        tasks.append("mantener marco neutral hasta que el usuario indique partido")
    return tasks


def _domain(goal: str) -> str:
    if goal in {
        "population_max_section",
        "elderly_population_max_section",
        "population_change_between_years",
        "income_change_between_years",
    }:
        return "demographic_analysis"
    if goal == "electoral_change_between_years":
        return "electoral_strategy"
    if goal == "ambiguous_change_between_years":
        return "analytical_clarification"
    if goal == "unknown_or_conversational":
        return "conversational"
    if goal in {
        "campaign_plan",
        "candidate_visit_plan",
        "party_growth_opportunity",
        "abstention_analysis",
        "mobilization_strategy",
        "persuasion_strategy",
        "electoral_diagnosis",
    }:
        return "electoral_strategy"
    if goal in {"commercial_targeting", "service_launch", "territorial_marketing"}:
        return "territorial_marketing"
    if goal == "public_service_outreach":
        return "public_service"
    if goal == "labor_training_outreach":
        return "public_service"
    if goal == "demographic_targeting":
        return "demographic"
    if goal == "sports_facilities_planning":
        return "sports_facilities_planning"
    if goal == "real_estate_location_advice":
        return "real_estate_location_advice"
    if goal == "urban_planning":
        return "urban_planning"
    if goal == "socioeconomic_analysis":
        return "socioeconomic_analysis"
    return "territorial"


_TERRITORIAL_DATA_GOALS = {
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


def _target_service(text: str) -> str | None:
    if re.search(r"ingles|inglés|english", text) and re.search(r"curso|clase|course", text):
        return "free English course" if re.search(r"gratis|gratuito|free", text) else "English course"
    if "academia" in text:
        return "academia"
    if re.search(r"servicio|service", text):
        return "local service"
    return None


def _target_audience(text: str) -> list[str]:
    audience: list[str] = []
    if re.search(r"ingles|inglés|english|curso|clase|academia", text):
        audience.extend(["families", "students", "young adults", "foreign residents"])
    if re.search(r"familias|hijos|ninos|niños", text):
        audience.append("families")
    if re.search(r"adolescentes|estudiantes|jovenes|jóvenes", text):
        audience.extend(["students", "young adults"])
    if re.search(r"mayores", text):
        audience.append("older residents")
    if re.search(r"extranjera|extranjeros|foreign", text):
        audience.append("foreign residents")
    return list(dict.fromkeys(audience))


def _municipality_id(value: str, text: str) -> str:
    if value.strip().lower() in {"mijas", "29070"} or "mijas" in text:
        return "29070"
    return value.strip()


def _extract_party(text: str) -> str | None:
    for party, aliases in {
        "PP": ["pp", "partido popular"],
        "PSOE": ["psoe", "partido socialista", "socialista"],
        "VOX": ["vox"],
        "CS": ["cs", "ciudadanos"],
    }.items():
        if any(re.search(rf"(^|[^a-z0-9]){re.escape(alias)}([^a-z0-9]|$)", text) for alias in aliases):
            return party
    return None


def _normalize(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn"
    )


def _is_conversational_message(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"(hola|buenas|buenos dias|buen dia|buenas tardes|buenas noches|gracias|muchas gracias|"
            r"vale|ok|okay|perfecto|de acuerdo|empezar|ayudame|ayuda|help|hey|hello|hi)",
            text,
        )
        or re.search(r"quien eres|que puedes hacer|dime preguntas|ayudame", text)
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


def _clarification_question(goal: str, text: str) -> str | None:
    if goal == "unknown_or_conversational":
        return (
            "Podemos empezar por algo sencillo: población, edad, renta, voto, abstención, vivienda, "
            "crecimiento urbano o comunicación territorial. ¿Qué tema quieres explorar primero?"
        )
    if goal != "ambiguous_change_between_years":
        return None
    years = re.findall(r"20\d{2}", text)
    if len(years) >= 2:
        return f"¿Te refieres a cambio demográfico, cambio electoral, cambio de renta o cambio urbanístico entre {years[0]} y {years[1]}?"
    return "¿Te refieres a cambio demográfico, cambio electoral, cambio de renta o cambio urbanístico?"


def _years(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"20\d{2}", text)]
