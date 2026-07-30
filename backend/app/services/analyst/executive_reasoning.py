from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.analyst.planner import PoliticalPlan
from app.services.analyst.schemas import AnalystSection
from app.services.analyst.tools import AnalystToolResult


@dataclass(slots=True)
class ExecutiveReasoning:
    executive_thesis: str
    political_reading: str
    strategic_decision: str
    territorial_logic: str
    recommended_actions: list[str] = field(default_factory=list)
    what_not_to_do: list[str] = field(default_factory=list)
    data_support: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, object]:
        return {
            "executive_thesis": self.executive_thesis,
            "political_reading": self.political_reading,
            "strategic_decision": self.strategic_decision,
            "territorial_logic": self.territorial_logic,
            "recommended_actions": self.recommended_actions,
            "what_not_to_do": self.what_not_to_do,
            "data_support": self.data_support,
            "limitations": self.limitations,
        }


class ExecutiveReasoningLayer:
    def reason(
        self,
        *,
        message: str,
        plan: PoliticalPlan | None,
        tool_result: AnalystToolResult,
        sections: list[AnalystSection],
    ) -> ExecutiveReasoning:
        goal = plan.goal if plan else "general_political_advice"
        party = plan.target_party if plan and plan.target_party else _extract_party(message) or "la candidatura"
        top = _dedupe_sections(sections)[:5]
        names = ", ".join(section.name for section in top[:4]) or "pocas secciones prioritarias"
        if plan and plan.domain not in {"electoral", "electoral_strategy"}:
            if plan.goal == "sports_facilities_planning":
                return ExecutiveReasoning(
                    executive_thesis=f"Sí. Para instalaciones deportivas empezaría por {names}, usando criterios de necesidad y accesibilidad, no de promoción.",
                    political_reading=(
                        "La lógica es de servicio público territorial: población joven, densidad, crecimiento residencial, presión urbana "
                        "y posible falta de equipamiento de proximidad."
                    ),
                    strategic_decision="Priorizar un estudio de demanda y suelo en 3-5 zonas antes de decidir inversión.",
                    territorial_logic=f"El primer mapa operativo lo forman {names}.",
                    recommended_actions=[
                        "Contrastar demanda juvenil y vecinal por sección.",
                        "Revisar accesibilidad peatonal y distancia a equipamientos existentes.",
                        "Validar disponibilidad de suelo y coste de mantenimiento.",
                        "Plantear una fase piloto de equipamiento deportivo de proximidad.",
                    ],
                    what_not_to_do=[
                        "No tratarlo como una campaña de marketing.",
                        "No decidir solo por población total.",
                        "No cerrar inversión sin inventario real de equipamientos y suelo.",
                    ],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["Faltan inventario de instalaciones, suelo disponible y datos de uso deportivo; se usan proxies demográficos y urbanos."],
                )
            if plan.goal == "real_estate_location_advice":
                return ExecutiveReasoning(
                    executive_thesis=f"Sí. Para comprar vivienda acotaría primero {names}, y después evaluaría inmueble por inmueble.",
                    political_reading=(
                        "La lógica no es promocional ni electoral: combina crecimiento residencial, servicios, renta del entorno, "
                        "densidad, calidad urbana y posible revalorización."
                    ),
                    strategic_decision="Usar el ranking para acotar visitas, no para comprar automáticamente.",
                    territorial_logic=f"El primer mapa residencial lo forman {names}.",
                    recommended_actions=[
                        "Comparar precio por metro, servicios cercanos, movilidad y ruido.",
                        "Revisar estado del edificio, comunidad y financiación.",
                        "Distinguir compra para vivir de compra para invertir.",
                    ],
                    what_not_to_do=[
                        "No comprar solo por un ranking territorial.",
                        "No confundir crecimiento residencial con buena compra automática.",
                        "No mezclar esta decisión con plantillas de campaña o promoción.",
                    ],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["No es tasación ni asesoramiento financiero; faltan precio real del inmueble, estado y condiciones de compra."],
                )
            if plan.goal == "labor_training_outreach":
                return ExecutiveReasoning(
                    executive_thesis=(
                        f"Sí. Para una formación dirigida a personas en edad laboral empezaría por {names}, "
                        "pero no por ser zonas jóvenes: por señales de potencial productivo, empleabilidad y necesidad de recualificación."
                    ),
                    political_reading=(
                        "La lógica es socioeconómica: combinar población en edad activa potencial, empleo/desempleo, perfil ocupacional, "
                        "complejidad productiva, renta y facilidad de activación comunitaria."
                    ),
                    strategic_decision="Priorizar secciones donde la formación pueda conectar necesidad laboral con oportunidad productiva local.",
                    territorial_logic=f"El primer mapa operativo lo forman {names}.",
                    recommended_actions=[
                        "Coordinar servicios de empleo y orientación profesional.",
                        "Usar centros municipales, asociaciones vecinales y comercios de proximidad.",
                        "Colaborar con empresas locales si el perfil profesional encaja.",
                        "Medir consultas, inscripciones y asistencia por sección.",
                    ],
                    what_not_to_do=[
                        "No usar una plantilla de familias, colegios o AMPAs.",
                        "No centrar la recomendación solo en población joven, crecimiento o densidad.",
                        "No prometer variables laborales si la capa socioeconómica no las aporta para una sección concreta.",
                    ],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["La priorización usa Inteligencia Socioeconómica y proxies territoriales; no sustituye registros administrativos individuales de empleo o demanda formativa."],
                )
            if plan.goal in {"territorial_marketing", "service_launch", "commercial_targeting"}:
                service = plan.target_service or "la iniciativa local"
                audience = ", ".join(plan.target_audience) if plan.target_audience else "usuarios potenciales del territorio"
                return ExecutiveReasoning(
                    executive_thesis=(
                        f"Sí. Para {service}, no lo promocionaría por todo Mijas de forma homogénea: "
                        f"empezaría por {names}, buscando {audience} y canales locales de alta confianza."
                    ),
                    political_reading="La lógica es de comunicación local: detectar demanda probable, facilidad de contacto y respuesta medible por zona.",
                    strategic_decision="Hacer una prueba piloto territorial en 3-5 zonas, medir contactos y ampliar solo donde haya respuesta.",
                    territorial_logic=f"El primer mapa operativo lo forman {names}.",
                    recommended_actions=[
                        "Promoción hiperlocal con mensaje simple y canal de contacto claro.",
                        "Colaboraciones con comercios, asociaciones y grupos vecinales.",
                        "Anuncios geolocalizados de radio corto para reforzar la difusión física.",
                        "Medición por zona: contactos, reservas, asistencia y coste por usuario potencial.",
                    ],
                    what_not_to_do=[
                        "No difundir de forma homogénea por todo Mijas.",
                        "No invertir en publicidad sin segmentación territorial.",
                        "No ampliar presupuesto sin medir respuesta por zona.",
                    ],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["Faltan indicadores directos de demanda educativa u origen; se usan proxies demográficos y territoriales."],
                )
            if plan.goal == "public_service_outreach":
                return ExecutiveReasoning(
                    executive_thesis=(
                        f"Sí. Para una comunicación pública, empezaría por {names}; no la plantearía como una promoción comercial, "
                        "sino como una acción de información útil para vecinos que pueden necesitarla."
                    ),
                    political_reading=(
                        "La lógica es de alcance público: vulnerabilidad socioeconómica probable, facilidad de contacto comunitario "
                        "y presencia de canales municipales o asociativos."
                    ),
                    strategic_decision="Concentrar la primera oleada en 3-5 zonas y validar si la información llega a las personas destinatarias.",
                    territorial_logic=f"El primer mapa operativo lo forman {names}.",
                    recommended_actions=[
                        "Coordinar servicios sociales, centros municipales y oficinas de empleo.",
                        "Usar asociaciones vecinales, comercios de proximidad y cartelería en equipamientos públicos.",
                        "Acompañar la comunicación con mensajes claros sobre requisitos, plazos y lugar de atención.",
                    ],
                    what_not_to_do=[
                        "No tratar ayudas públicas como una campaña comercial.",
                        "No usar mensajes de prueba gratuita, reserva o captación de clientes.",
                        "No depender solo de publicidad digital si hay barreras de acceso a la información.",
                    ],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["La priorización usa indicadores socioeconómicos y territoriales disponibles; no sustituye a los registros administrativos reales de demandantes."],
                )
            if plan.goal == "demographic_targeting":
                return ExecutiveReasoning(
                    executive_thesis=f"Sí. Empezaría por {names}, separando el análisis por el grupo demográfico que se quiera alcanzar.",
                    political_reading="La lógica es demográfica y territorial: edad, densidad, crecimiento y renta ayudan a localizar públicos probables.",
                    strategic_decision="Definir primero el grupo objetivo y después validar canales concretos por zona.",
                    territorial_logic=f"El primer mapa operativo lo forman {names}.",
                    recommended_actions=[
                        "Contrastar el perfil demográfico con servicios y espacios de proximidad.",
                        "Adaptar el mensaje al grupo objetivo sin asumir datos no disponibles.",
                        "Medir respuesta por zona antes de ampliar la acción.",
                    ],
                    what_not_to_do=["No usar una plantilla comercial si la pregunta es de perfil territorial."],
                    data_support=_data_support(tool_result.rows[:5]),
                    limitations=["La priorización usa proxies demográficos y territoriales; conviene validarla con conocimiento local."],
                )
            return ExecutiveReasoning(
                executive_thesis=f"Sí. Para una decisión territorial general, empezaría por {names} y validaría en campo antes de invertir recursos.",
                political_reading="La lógica es territorial: población, crecimiento, densidad, renta y entorno urbano orientan dónde mirar primero.",
                strategic_decision="Usar el ranking como primera criba, no como decisión final automática.",
                territorial_logic=f"El primer mapa operativo lo forman {names}.",
                recommended_actions=[
                    "Comparar indicadores territoriales disponibles.",
                    "Validar servicios cercanos y condiciones reales de la zona.",
                    "Definir un objetivo operativo antes de ejecutar la acción.",
                ],
                what_not_to_do=[
                    "No forzar un marco electoral o comercial si la pregunta no lo pide.",
                    "No repetir una plantilla de promoción cuando el objetivo no es captar clientes.",
                ],
                data_support=_data_support(tool_result.rows[:5]),
                limitations=["La priorización es una primera lectura territorial; debe contrastarse con información operativa específica."],
            )
        if goal == "abstention_analysis":
            first = top[0].name if top else "la sección con mayor abstención"
            return ExecutiveReasoning(
                executive_thesis=f"La prioridad es tratar {first} como una operación de movilización, no como una campaña genérica.",
                political_reading="La abstención alta señala fricción electoral: votantes que pueden activarse con presencia, recordatorio y contacto local.",
                strategic_decision="Ordenar las secciones por abstención y concentrar ahí puerta a puerta, llamadas y recordatorio de voto.",
                territorial_logic=f"El primer bloque territorial es {names}.",
                recommended_actions=[
                    "Puerta a puerta con mensaje de problemas concretos del barrio.",
                    "Recordatorio de voto en la semana final.",
                    "Captación de contactos y seguimiento por sección.",
                ],
                what_not_to_do=["No confundir abstención con persuasión ideológica pura."],
                data_support=_data_support(tool_result.rows[:5]),
                limitations=["La abstención observada no garantiza conversión automática en votos."],
            )
        if goal == "candidate_visit_plan":
            return ExecutiveReasoning(
                executive_thesis=f"Empezaría la agenda del candidato por {names}, con visitas cortas, repetidas y muy preparadas.",
                political_reading="Una visita vale si produce relación política: escucha, contactos, problemas localizados y compromiso visible.",
                strategic_decision="Priorizar 3 a 5 secciones y repetir presencia antes que hacer una gira dispersa.",
                territorial_logic=f"El orden sale de combinar oportunidad, abstención, margen competitivo y tamaño territorial: {names}.",
                recommended_actions=[
                    "Paseo de candidato con vecinos identificados.",
                    "Reuniones pequeñas por zona.",
                    "Cierre de cada visita con lista de contactos y seguimiento.",
                ],
                what_not_to_do=["No hacer actos grandes sin conversión territorial medible."],
                data_support=_data_support(tool_result.rows[:5]),
                limitations=["Conviene validar la agenda con conocimiento local antes de cerrar horarios y formatos."],
            )
        return ExecutiveReasoning(
            executive_thesis=(
                f"Sí. Para {party} no intentaría cubrir todo Mijas: concentraría el esfuerzo en {names}, "
                "con alta repetición, presencia del candidato y mensajes diferenciados por tipo de votante."
            ),
            political_reading=(
                "La campaña debe separar movilización, persuasión y retención. Cada sección tiene un trabajo político distinto: "
                "activar abstención, convencer en márgenes estrechos o reforzar base propia."
            ),
            strategic_decision="La decisión es concentrar recursos en pocas secciones y medir respuesta antes de ampliar gasto.",
            territorial_logic=f"El primer mapa operativo lo forman {names}.",
            recommended_actions=[
                "Puerta a puerta y presencia de calle en zonas de movilización.",
                "Agenda del candidato y reuniones pequeñas en zonas disputadas.",
                "Publicidad digital hiperlocal solo como repetición del mensaje territorial.",
                "Recordatorio de voto en cierre de campaña.",
            ],
            what_not_to_do=[
                "No dispersar presupuesto por todo el municipio.",
                "No hacer comunicación genérica sin aterrizaje por sección.",
                "No sustituir presencia territorial por anuncios digitales.",
            ],
            data_support=_data_support(tool_result.rows[:5]),
            limitations=["Es una priorización operativa con datos internos disponibles, no una encuesta ni una predicción cerrada."],
        )


def _data_support(rows: list[dict[str, Any]]) -> list[str]:
    support: list[str] = []
    for row in rows:
        name = str(row.get("section_name") or row.get("section_id") or "").strip()
        if not name:
            continue
        bits = []
        if row.get("abstention_rate_pct") is not None:
            bits.append(f"abstención {_fmt(row.get('abstention_rate_pct'))}%")
        if row.get("target_party_vote_pct") is not None:
            bits.append(f"voto objetivo {_fmt(row.get('target_party_vote_pct'))}%")
        if row.get("victory_margin_pct") is not None:
            bits.append(f"margen {_fmt(row.get('victory_margin_pct'))} puntos")
        if row.get("under_30_pct") is not None:
            bits.append(f"jóvenes {_fmt(row.get('under_30_pct'))}%")
        if row.get("population_growth_pct") is not None:
            bits.append(f"crecimiento {_fmt(row.get('population_growth_pct'))}%")
        if row.get("population_total") is not None:
            bits.append(f"población {row.get('population_total')}")
        support.append(f"{name}: " + (", ".join(bits) if bits else "evidencia territorial disponible"))
    return support


def _dedupe_sections(sections: list[AnalystSection]) -> list[AnalystSection]:
    seen: set[str] = set()
    output: list[AnalystSection] = []
    for section in sections:
        if section.section_id in seen:
            continue
        seen.add(section.section_id)
        output.append(section)
    return output


def _extract_party(message: str) -> str | None:
    lowered = message.lower()
    for party in ["PP", "PSOE", "VOX"]:
        if party.lower() in lowered:
            return party
    return None


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return ""
