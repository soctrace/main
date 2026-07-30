from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from app.services.analyst.schemas import AnalystChatRequest, AnalystChatResponse
from app.services.orchestrator.context_store import AnalyticalExplanationContext, context_store
from app.services.orchestrator.methodology_explanation import MethodologyExplanationLayer


QuestionType = Literal["standalone_definition", "followup_explanation", "analytical", "ambiguous"]


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


@dataclass(frozen=True, slots=True)
class MethodologyDefinition:
    label: str
    variables: tuple[str, ...]
    definition: str
    calculation: str
    interpretation: str
    limitations: str


@dataclass(frozen=True, slots=True)
class MethodologyClassification:
    handled: bool
    question_type: QuestionType
    reason: str
    indicator: str | None = None


def _definition(label: str, variables: tuple[str, ...], definition: str, calculation: str, interpretation: str, limitations: str) -> MethodologyDefinition:
    return MethodologyDefinition(label, variables, definition, calculation, interpretation, limitations)


METHODOLOGY_CATALOG: dict[str, MethodologyDefinition] = {
    "densidad de poblacion": _definition("densidad de población", ("population_density",), "Indica cuántas personas residen, en promedio, por unidad de superficie.", "Se divide la población residente entre la superficie del territorio, normalmente en km².", "Un valor alto señala mayor concentración residencial; no describe por sí solo hacinamiento ni calidad urbana.", "Depende del año de población y de la geometría territorial usada."),
    "edad media": _definition("edad media", ("average_age",), "Resume la edad promedio de la población residente.", "Se suman las edades ponderadas por el número de personas de cada edad y se divide entre la población total.", "Permite comparar estructuras demográficas, pero no sustituye la distribución completa por edades.", "Puede ocultar diferencias entre generaciones o grupos con tamaños distintos."),
    "poblacion menor de 30 anos": _definition("población menor de 30 años", ("population_under_30", "population_under_30_pct"), "Mide las personas residentes con menos de 30 años.", "El porcentaje divide esa población entre la población total y multiplica el resultado por 100.", "Valores altos indican una estructura relativamente joven.", "No informa por sí solo sobre estudios, empleo o intención electoral."),
    "poblacion mayor de 65 anos": _definition("población mayor de 65 años", ("population_over_65", "population_over_65_pct"), "Mide las personas residentes de 65 años o más.", "El porcentaje divide ese grupo entre la población total y multiplica el resultado por 100.", "Valores altos indican mayor peso relativo de población sénior.", "No equivale a dependencia, discapacidad ni necesidad individual de cuidados."),
    "crecimiento de poblacion": _definition("crecimiento de población", ("population_absolute_change", "population_growth_pct"), "Describe la variación de población entre dos periodos.", "El cambio absoluto resta población inicial a final; el porcentaje divide esa diferencia entre la población inicial y multiplica por 100.", "Un valor positivo indica crecimiento y uno negativo, descenso.", "Las comparaciones requieren territorios compatibles entre años."),
    "distribucion por sexo": _definition("distribución por sexo", ("population_by_sex",), "Describe el reparto agregado de la población según las categorías disponibles en la fuente.", "Se cuentan las personas de cada categoría y, si se expresa en porcentaje, se divide cada grupo entre el total.", "Sirve para comparar composición poblacional agregada.", "La disponibilidad y categorías dependen de la fuente estadística."),
    "participacion electoral": _definition("participación electoral", ("participation_pct",), "Es la proporción del censo electoral que emitió voto.", "Se dividen los votos emitidos entre el censo electoral y se multiplica por 100.", "Un valor alto indica mayor movilización electoral agregada.", "No permite inferir por qué votó o se abstuvo cada persona."),
    "abstencion": _definition("abstención", ("abstention_pct",), "Es la proporción del censo electoral que no emitió voto.", "Se resta el número de votantes al censo, se divide entre el censo y se multiplica por 100.", "Valores altos indican menor participación agregada.", "No identifica motivos individuales ni preferencias políticas."),
    "margen electoral": _definition("margen electoral", ("victory_margin_pct",), "Es la distancia entre el porcentaje del primer y segundo partido.", "Se resta el porcentaje de voto del segundo partido al del ganador.", "Un margen pequeño señala una competición más ajustada.", "Depende de la elección y no predice automáticamente resultados futuros."),
    "partido ganador": _definition("partido ganador", ("winner_party",), "Es la candidatura con más votos válidos en el territorio y elección consultados.", "Se comparan los votos de todas las candidaturas y se selecciona el máximo.", "Identifica la primera fuerza, no necesariamente una mayoría absoluta ni el gobierno resultante.", "Los empates y reglas institucionales requieren tratamiento adicional."),
    "bloque izquierda derecha": _definition("bloque izquierda/derecha", ("ideological_block",), "Agrupa candidaturas mediante una clasificación ideológica declarada.", "Se suman votos o porcentajes de los partidos asignados a cada bloque.", "Facilita una lectura agregada del equilibrio político.", "La clasificación es una convención analítica y puede simplificar posiciones políticas diversas."),
    "voto local nacional": _definition("voto local/nacional", ("local_national_vote",), "Compara el comportamiento agregado entre elecciones de distinto ámbito.", "Se contrastan porcentajes de candidaturas equivalentes en elecciones locales y nacionales compatibles.", "Muestra diferencias territoriales entre ámbitos electorales.", "Las candidaturas, participación y contexto pueden no ser directamente equivalentes."),
    "fragmentacion electoral": _definition("fragmentación electoral", ("electoral_fragmentation",), "Describe cuánto se reparte el voto entre varias candidaturas.", "Se calcula con la distribución de cuotas de voto; una medida habitual deriva de la suma de sus cuadrados.", "Mayor fragmentación implica voto más repartido y menor concentración.", "El resultado depende de la medida elegida y de qué candidaturas se incluyan."),
    "ley dhondt": _definition("Ley D'Hondt", ("dhondt_quotients",), "Es un método de reparto proporcional de escaños mediante cocientes sucesivos.", "Los votos de cada candidatura se dividen por 1, 2, 3 y siguientes; los escaños se asignan a los cocientes más altos.", "Favorece moderadamente a candidaturas con más votos frente a métodos más proporcionales.", "También influyen barreras electorales, circunscripción y número de escaños."),
    "renta media individual": _definition("renta media individual", ("income_individual",), "Es la renta media atribuida a cada persona según la fuente estadística.", "Se divide la renta agregada considerada entre la población correspondiente.", "Permite comparar capacidad económica media entre territorios.", "No representa la renta exacta de cada residente y puede ocultar desigualdad."),
    "renta media por hogar": _definition("renta media por hogar", ("income_household",), "Es la renta media disponible o declarada por hogar según la fuente.", "Se divide la renta agregada de los hogares entre el número de hogares considerados.", "Ayuda a comparar recursos económicos medios de los hogares.", "Depende del tamaño del hogar y no describe la distribución interna de rentas."),
    "quintiles de renta": _definition("quintiles de renta", ("income_quintile",), "Dividen los territorios ordenados por renta en cinco grupos de tamaño similar.", "Se ordenan los valores y se asignan cortes del 20 % desde el grupo inferior al superior.", "Permiten interpretar posición relativa, no diferencias absolutas.", "Los cortes cambian con el universo y periodo analizados."),
    "ocupacion": _definition("ocupación", ("occupation",), "Describe la situación o estructura ocupacional agregada disponible.", "Se calculan recuentos o porcentajes por categoría respecto al total aplicable.", "Muestra la composición laboral del territorio.", "Las categorías y población de referencia dependen de la fuente."),
    "nivel de estudios": _definition("nivel de estudios", ("education_level",), "Resume el nivel educativo alcanzado en categorías agregadas.", "Se calcula el peso de cada categoría sobre la población de referencia.", "Permite comparar perfiles educativos territoriales.", "No mide por sí solo competencias, calidad educativa ni empleo."),
    "actividad economica": _definition("actividad económica", ("economic_activity",), "Describe la participación o composición de la población en actividades económicas.", "Se agregan personas o unidades por situación y se calculan porcentajes sobre la población aplicable.", "Ayuda a interpretar el perfil productivo y laboral.", "La definición exacta depende de la fuente y periodo."),
    "densidad de parcelas": _definition("densidad de parcelas", ("parcel_density",), "Mide cuántas parcelas existen por unidad de superficie.", "Se divide el número de parcelas entre la superficie territorial.", "Valores altos suelen reflejar un tejido más parcelado.", "No informa por sí sola sobre uso, edificabilidad o ocupación real."),
    "huella construida": _definition("huella construida", ("built_footprint",), "Es la superficie del suelo ocupada por la proyección de las edificaciones.", "Se suma el área de las geometrías de edificios dentro del territorio.", "Indica cuánto suelo está físicamente ocupado por construcciones.", "Depende de la cobertura y fecha de la cartografía de edificios."),
    "parcela media": _definition("parcela media", ("avg_plot_size",), "Es la superficie promedio de las parcelas del territorio.", "Se divide la superficie total de parcelas entre su número.", "Ayuda a distinguir tejidos de parcela pequeña o grande.", "La media puede verse afectada por parcelas excepcionalmente extensas."),
    "intensidad edificatoria": _definition("intensidad edificatoria", ("building_intensity",), "Relaciona la superficie construida con la superficie de suelo considerada.", "Se divide la superficie construida total entre la superficie de parcela o territorio, según la fuente.", "Valores altos indican mayor intensidad de construcción.", "No equivale necesariamente a densidad residencial ni altura media."),
    "valor catastral estimado por m2": _definition("valor catastral estimado por m²", ("cadastral_value_estimated_m2",), "Es una aproximación territorial del valor catastral por superficie.", "Se relaciona el valor catastral agregado disponible con los metros cuadrados correspondientes.", "Permite comparaciones orientativas entre territorios.", "No es una valoración individual ni sustituye la información oficial de cada inmueble."),
    "precio de mercado estimado por m2": _definition("precio de mercado estimado por m²", ("market_price_estimated_m2",), "Es una estimación del precio de mercado por metro cuadrado.", "Se obtiene de valores agregados o modelizados y se normaliza por superficie.", "Sirve para comparar niveles relativos de mercado.", "No es una tasación oficial y depende de cobertura, periodo y método de estimación."),
    "ratio mercado catastro": _definition("ratio mercado/catastro", ("market_cadastral_ratio",), "Compara el valor estimado de mercado con el valor catastral.", "Se divide el valor de mercado estimado entre el valor catastral comparable.", "Un ratio superior a uno indica que la estimación de mercado supera el valor catastral.", "Ambos valores deben corresponder a conceptos y periodos compatibles."),
}


_ALIASES = {
    "densidad": "densidad de poblacion", "margen entre partidos": "margen electoral",
    "ley d'hondt": "ley dhondt", "dhondt": "ley dhondt", "participacion": "participacion electoral",
    "renta por hogar": "renta media por hogar", "renta individual": "renta media individual",
    "bloque izquierda/derecha": "bloque izquierda derecha", "voto local/nacional": "voto local nacional",
    "valor catastral por m2": "valor catastral estimado por m2", "precio de mercado por m2": "precio de mercado estimado por m2",
}


def _indicator_in(text: str) -> str | None:
    candidates = {**{key: key for key in METHODOLOGY_CATALOG}, **_ALIASES}
    matches = [(alias, canonical) for alias, canonical in candidates.items() if alias in text]
    return max(matches, key=lambda item: len(item[0]))[1] if matches else None


def classify_methodology_question(message: str, conversation_id: str | None = None) -> MethodologyClassification:
    text = _normalize(message)
    state = context_store.get(conversation_id) if conversation_id else None
    concrete = (
        r"\b(?:19|20)\d{2}\b", r"\bseccion(?:es)?\s+\d+\b", r"\b(pp|psoe|vox|sumar|podemos|ciudadanos)\b",
        r"\b(compara|comparar|frente a|versus|ranking|ordena|mejor resultado)\b",
        r"\b(que|cual|donde)\b.*\b(seccion|zona)\b.*\b(mayor|menor|mas|menos)\b",
        r"\b(evolucion|evolucionado|cambiado|desde|hasta)\b", r"\b(cuanto|cuanta|que renta tiene|que valor tiene)\b",
        r"\bpor que\b.*\bseccion\b", r"\bresultado electoral\b.*\bseccion\b",
    )
    if any(re.search(pattern, text) for pattern in concrete):
        return MethodologyClassification(False, "analytical", "requires_concrete_data")

    indicator = _indicator_in(text)
    definition_intent = bool(re.search(r"\b(que es|que significa|como se calcula|como se obtiene|como se mide)\b", text))
    if indicator and definition_intent:
        return MethodologyClassification(True, "standalone_definition", "known_indicator_definition", indicator)

    if state and MethodologyExplanationLayer().explain(message, state) is not None:
        return MethodologyClassification(True, "followup_explanation", "supported_by_previous_analysis")
    if re.search(r"\b(como has calculado|que formula|que variables|que fuente|ese resultado|ese indicador|por que aparece)\b", text):
        return MethodologyClassification(False, "ambiguous", "missing_analytical_context")
    return MethodologyClassification(False, "analytical", "not_methodology")


class MethodologyInterceptor:
    def try_handle(self, payload: AnalystChatRequest) -> tuple[AnalystChatResponse | None, MethodologyClassification]:
        classification = classify_methodology_question(payload.message, payload.conversation_id)
        if not classification.handled:
            return None, classification
        if classification.question_type == "standalone_definition":
            definition = METHODOLOGY_CATALOG[classification.indicator or ""]
            answer = " ".join((definition.definition, definition.calculation, definition.interpretation, definition.limitations))
            return AnalystChatResponse(
                answer=answer,
                methodology=f"Definición general de {definition.label}; no se consultaron datos concretos, SQL, herramientas ni modelos de lenguaje.",
                confidence="high", display_mode="chat", variables_used=list(definition.variables),
                limitations=[definition.limitations, "Explicación general: no se consultaron datos territoriales concretos."],
                follow_up_questions=[f"¿Cómo se interpreta {definition.label}?", f"¿Qué limitaciones tiene {definition.label}?"],
                conversation_id=payload.conversation_id or str(uuid4()), audit_id="methodology_explanation_layer",
            ), classification
        state = context_store.get(payload.conversation_id or "")
        explanation = MethodologyExplanationLayer().explain(payload.message, state)
        if explanation is None:
            return None, MethodologyClassification(False, "ambiguous", "explanation_not_available")
        return AnalystChatResponse(
            answer=explanation.answer,
            methodology="Explicación del análisis anterior; no se ejecutaron SQL, herramientas, planner ni modelos de lenguaje.",
            confidence="high", display_mode="chat", variables_used=list(state.last_variables_used),
            data_layers_used=list(state.last_data_layers_used), limitations=list(state.methodology_explanation.warnings),
            follow_up_questions=["¿Qué fuente se utilizó?", "¿Qué limitaciones tiene el resultado?"],
            conversation_id=payload.conversation_id, audit_id="methodology_explanation_layer",
        ), classification

    def remember(self, payload: AnalystChatRequest, response: AnalystChatResponse) -> None:
        conversation_id = payload.conversation_id or response.conversation_id
        if not conversation_id or not response.tools_used:
            return
        state = context_store.get(conversation_id)
        state.last_user_goal = payload.message[:200]
        state.last_topic = payload.context.active_layer or "analytical"
        state.last_tools_used = list(response.tools_used)
        state.last_data_layers_used = list(response.data_layers_used)
        state.last_variables_used = list(response.variables_used)
        state.last_source_views = list(response.data_used)
        state.last_answer_summary = f"Análisis territorial para {payload.context.active_year or 'el periodo disponible'}"
        state.methodology_explanation = AnalyticalExplanationContext(
            methodology=response.methodology[:1000], warnings=list(response.limitations or response.warnings),
            metric=response.variables_used[0] if response.variables_used else None, year=payload.context.active_year,
            territory=payload.municipality_id, operation=response.tools_used[0], response_type=response.display_mode,
        )


methodology_interceptor = MethodologyInterceptor()
