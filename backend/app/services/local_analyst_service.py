from dataclasses import dataclass
import logging
import re
import unicodedata

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.analyst_repository import AnalystRepository
from app.repositories.forecast_repository import ForecastRepository
from app.schemas.analyst import AnalystAnswer, AnalystChartSpec, AnalystTable
from app.services.dataset_access import ApprovedDatasetAccess
from app.services.municipality_pack_service import MunicipalityPackService


logger = logging.getLogger(__name__)

LOCAL_ANALYST_SYSTEM_PROMPT = """
Eres SocTrace Local Analyst para Mijas. No inventes datos ni uses informacion
externa. Si falta informacion, dilo. Distingue siempre dato observado, estimado
y forecast. No respondas con tablas sin explicacion. Traduce resultados
tecnicos a lenguaje comprensible. Actua con rigor como data scientist,
estadistico, sociologo, economista territorial y analista electoral. No adules
al usuario. No conviertas hipotesis politicas en hechos. Si hay incertidumbre,
explicala.
""".strip()

TOOLS = {
    "sql": "approved_sql_query_tool",
    "forecast": "forecast_engine",
    "dhondt": "dhondt_calculator",
    "rag": "municipality_context_retriever",
    "chart": "chart_spec_generator",
    "methodology": "methodology_retriever",
    "planner": "local_query_planner",
    "analytics": "local_analytical_engine",
}


def normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )


class IntentRouter:
    def detect(self, question: str) -> str:
        text = normalize(question)
        has_party = bool(extract_party(question))
        has_section_reference = bool(extract_section_hint(question))
        asks_party_dominance = bool(
            re.search(r"histor|suelen votar|a quien votan|a quién votan|mas votado|más votado|primera fuerza", text)
            and re.search(r"vot|partido|fuerza", text)
        )
        asks_youngest_section_context = bool(re.search(r"joven|young", text))
        if asks_party_dominance and (has_section_reference or asks_youngest_section_context or not has_party):
            return "historical_party_dominance_for_section"
        has_direction_or_trend = bool(extract_metric_direction(question)) or bool(
            re.search(r"evolucion|cuando|en que eleccion|en que elecciones|a lo largo del tiempo|across elections", text)
        )
        if has_party and has_section_reference and has_direction_or_trend:
            return "party_performance_by_section_across_elections"

        has_historical_average = bool(
            re.search(
                r"media|promedio|histor|todas las elecciones|todas las secciones|a lo largo del tiempo|en todas las elecciones|average|historical average",
                text,
            )
        )
        has_similarity = bool(re.search(r"simil|parecid|perfil|social|econom|renta|ingreso|demograf|vivienda|catastro", text))
        if has_historical_average and has_party and has_similarity:
            return "multi_step_electoral_socioeconomic_analysis"
        if has_historical_average and has_party:
            return "historical_party_average"
        if has_similarity and has_party:
            return "cross_variable_similarity"
        if re.search(r"demograf|edad|mayores|joven|poblacion|densidad", text) and not has_party:
            return "demographic_analysis"
        if re.search(r"renta|ingreso|income", text) and not has_party:
            return "income_analysis"
        if re.search(r"d\s*['’]?\s*hondt|concejal|reparto|escano|votos?.*concejal", text):
            return "electoral_calculation"
        if re.search(r"metodolog|como se calcula|fuente|limitacion|modelo", text):
            return "methodology_explanation"
        if re.search(r"forecast|prevision|proyeccion|escenario|2027|volatil|abstencion", text):
            return "forecast_question"
        if re.search(r"compar|versus| vs |diferencia|evolucion|2019.*2023|2023.*2019", text):
            return "section_comparison"
        if re.search(r"estrateg|prioridad|interpret|oportunidad|riesgo territorial", text):
            return "strategic_interpretation"
        if re.search(r"poblacion|densidad|renta|ingreso|participacion|psoe|pp|vox|voto|seccion|gano|ganar|fuerte", text):
            return "simple_electoral_ranking" if has_party else "data_lookup"
        return "unknown_or_unsupported"


class ToolPlanner:
    def plan(self, intent: str) -> list[str]:
        return {
            "simple_electoral_ranking": [TOOLS["sql"]],
            "party_performance_by_section_across_elections": [TOOLS["planner"], TOOLS["sql"], TOOLS["analytics"]],
            "historical_party_average": [TOOLS["planner"], TOOLS["sql"], TOOLS["analytics"]],
            "historical_party_dominance_for_section": [TOOLS["planner"], TOOLS["sql"], TOOLS["analytics"]],
            "cross_variable_similarity": [TOOLS["planner"], TOOLS["sql"], TOOLS["analytics"]],
            "multi_step_electoral_socioeconomic_analysis": [TOOLS["planner"], TOOLS["sql"], TOOLS["analytics"]],
            "demographic_analysis": [TOOLS["sql"]],
            "income_analysis": [TOOLS["sql"]],
            "data_lookup": [TOOLS["sql"]],
            "section_comparison": [TOOLS["sql"], TOOLS["chart"]],
            "electoral_calculation": [TOOLS["sql"], TOOLS["dhondt"]],
            "forecast_question": [TOOLS["forecast"]],
            "methodology_explanation": [TOOLS["methodology"]],
            "strategic_interpretation": [TOOLS["forecast"], TOOLS["rag"]],
            "unknown_or_unsupported": [],
        }[intent]


PARTY_ALIASES = {
    "PP": ["pp", "partido popular"],
    "PSOE": ["psoe", "psoe-a", "partido socialista", "partido socialista obrero espanol"],
    "VOX": ["vox"],
    "CS": ["cs", "ciudadanos"],
    "POR MI PUEBLO": ["por mi pueblo", "pmp"],
}


def extract_party(question: str) -> str | None:
    text = normalize(question)
    for party, aliases in PARTY_ALIASES.items():
        if any(re.search(rf"(^|[^a-z0-9]){re.escape(alias)}([^a-z0-9]|$)", text) for alias in aliases):
            return party
    return None


def extract_section_hint(question: str) -> str | None:
    text = normalize(question)
    section_id_match = re.search(r"\b29\d{8}\b", text)
    if section_id_match:
        return section_id_match.group(0)

    section_number_match = re.search(r"\b(?:seccion|section)\s+0?(\d{1,3})\b", text)
    if section_number_match:
        return section_number_match.group(1)

    # Named section references normally appear after location prepositions in
    # questions such as "en La Sierrezuela" or "en Cala de Mijas".
    named_match = re.search(r"\ben\s+(?!que\b)([a-z0-9][a-z0-9\s/·().-]{2,})$", text)
    if named_match and not re.fullmatch(r"\d{4}", named_match.group(1).strip()):
        return named_match.group(1).strip()

    return None


def extract_metric_direction(question: str) -> str:
    text = normalize(question)
    if re.search(r"\b(menos|menor|peor|minimo|mas bajo|lowest|worst)\b", text):
        return "min"
    if re.search(r"\b(mas|mayor|mejor|maximo|mas alto|highest|best)\b", text):
        return "max"
    if re.search(r"\b(evolucion|tendencia|trend|a lo largo del tiempo)\b", text):
        return "trend"
    return "trend"


@dataclass(frozen=True, slots=True)
class Quotient:
    party: str
    divisor: int
    value: float


class DHondtCalculator:
    def calculate(self, parties: list[dict], total_seats: int = 25, threshold_pct: float = 5) -> dict:
        total_votes = sum(int(item["votes"]) for item in parties)
        eligible = [
            {**item, "percentage": 100 * int(item["votes"]) / total_votes}
            for item in parties
            if total_votes and 100 * int(item["votes"]) / total_votes >= threshold_pct
        ]
        quotients = [
            Quotient(item["party"], divisor, int(item["votes"]) / divisor)
            for item in eligible
            for divisor in range(1, total_seats + 1)
        ]
        winners = sorted(quotients, key=lambda item: (-item.value, item.party, item.divisor))[:total_seats]
        seats: dict[str, int] = {}
        for item in winners:
            seats[item.party] = seats.get(item.party, 0) + 1
        return {"eligible": eligible, "winners": winners, "seats": seats}


class LocalAnalystService:
    def __init__(self, session: Session):
        self.repository = AnalystRepository(session)
        self.forecasts = ForecastRepository(session)
        self.datasets = ApprovedDatasetAccess()
        self.pack = MunicipalityPackService()
        self.router = IntentRouter()
        self.planner = ToolPlanner()
        self.dhondt = DHondtCalculator()

    def ask(self, question: str, municipality_id: str) -> AnalystAnswer:
        intent = self.router.detect(question)
        tools = self.planner.plan(intent)
        try:
            payload = self._answer(intent, question, municipality_id)
            audit_id = self.repository.audit(
                question=question,
                municipality_id=municipality_id,
                intent=intent,
                tools=tools,
                datasets=payload["data_origin"],
                answer=payload["answer"],
                confidence_level=payload["confidence_level"],
                methodological_notes=payload["methodological_notes"],
            )
            return AnalystAnswer(**payload, used_tools=tools, audit_id=audit_id)
        except Exception as exc:
            logger.exception("Local analyst failed", extra={"intent": intent})
            self.repository.session.rollback()
            payload = self._unsupported(
                "No puedo responder con rigor porque la consulta interna necesaria no esta disponible."
            )
            audit_id = self.repository.audit(
                question=question,
                municipality_id=municipality_id,
                intent=intent,
                tools=tools,
                datasets=[],
                answer=payload["answer"],
                confidence_level="low",
                methodological_notes=payload["methodological_notes"],
                error=str(exc),
            )
            return AnalystAnswer(**payload, used_tools=tools, audit_id=audit_id)

    def _answer(self, intent: str, question: str, municipality_id: str) -> dict:
        if municipality_id != "29070":
            return self._unsupported("El analista local disponible en esta version solo cubre Mijas.")
        if intent == "party_performance_by_section_across_elections":
            return self._party_performance_by_section(question, municipality_id)
        if intent == "historical_party_average":
            return self._historical_party_average(question, municipality_id, include_similarity=False)
        if intent == "historical_party_dominance_for_section":
            return self._historical_party_dominance_for_section(question, municipality_id)
        if intent == "cross_variable_similarity":
            return self._historical_party_average(question, municipality_id, include_similarity=True)
        if intent == "multi_step_electoral_socioeconomic_analysis":
            return self._historical_party_average(question, municipality_id, include_similarity=True)
        if intent == "electoral_calculation":
            return self._dhondt(municipality_id)
        if intent == "forecast_question":
            return self._forecast(municipality_id)
        if intent == "methodology_explanation":
            return self._methodology()
        if intent == "section_comparison":
            return self._turnout_comparison(municipality_id)
        if intent == "strategic_interpretation":
            return self._strategic(municipality_id)
        if intent == "simple_electoral_ranking":
            return self._data_lookup(question, municipality_id)
        if intent in {"data_lookup", "demographic_analysis", "income_analysis"}:
            return self._unsupported(
                "Puedo responder esa familia de preguntas cuando concretas una variable y un periodo. Para analisis electoral complejo, puedo calcular medias historicas por partido y compararlas con indicadores sociales y economicos."
            )
        return self._unsupported(
            "No dispongo de una herramienta interna aprobada para responder esa pregunta. Puedo explicar metodologia, comparar participacion municipal, describir el forecast o calcular el reparto D'Hondt."
        )

    def _dhondt(self, municipality_id: str) -> dict:
        datasets = ["core.resultados_seccion", "core.candidatura_alias"]
        parties = self.repository.get_municipal_party_votes(municipality_id)
        result = self.dhondt.calculate(parties)
        psoe = next((item for item in result["eligible"] if item["party"].upper().startswith("PSOE")), None)
        if not psoe:
            return self._unsupported("No encuentro votos observados del PSOE en las municipales de 2023.")
        seats = result["seats"].get(psoe["party"], 0)
        entered = {(item.party, item.divisor) for item in result["winners"]}
        rows = [
            [
                str(divisor),
                self._number(int(psoe["votes"])),
                self._number(psoe["votes"] / divisor, 2),
                "Si" if (psoe["party"], divisor) in entered else "No",
            ]
            for divisor in range(1, max(seats + 3, 8) + 1)
        ]
        return {
            "answer": (
                f"El PSOE obtuvo {seats} concejales con {self._number(psoe['votes'])} votos observados. "
                "No existe un numero fijo de votos por concejal: el metodo D'Hondt divide los votos de cada candidatura "
                "entre 1, 2, 3 y asi sucesivamente, y ordena todos los cocientes. Entran los 25 cocientes mas altos del conjunto municipal."
            ),
            "summary": f"Los cocientes PSOE que entran en el reparto son los correspondientes a sus primeros {seats} divisores.",
            "confidence_level": "high",
            "data_origin": datasets,
            "methodological_notes": [
                "Dato observado: votos municipales de 2023 agregados desde resultados internos por seccion.",
                "Calculo determinista: metodo D'Hondt con 25 concejales y umbral legal del 5%.",
                "La media votos/concejal puede calcularse, pero no representa el mecanismo real de asignacion.",
            ],
            "table": AnalystTable(
                title="Cocientes D'Hondt del PSOE en Mijas, municipales 2023",
                columns=["Divisor", "Votos PSOE", "Cociente", "Entra entre los 25"],
                rows=rows,
            ),
        }

    def _forecast(self, municipality_id: str) -> dict:
        datasets = ["marts.electoral_forecasting_municipality_2027"]
        self.datasets.require(*datasets)
        row = self.forecasts.get_municipality_outlook(municipality_id)
        if not row:
            return self._unsupported("No hay forecast municipal interno disponible para Mijas.")
        confidence = row["confidence_level"] if row["confidence_level"] in {"high", "medium", "low"} else "low"
        return {
            "answer": (
                f"El forecast estructural interno para 2027 situa como primera fuerza estimada a {row['projected_leading_party']} "
                f"con un {self._number(row['projected_leading_vote_share'], 1)}% y una participacion estimada del "
                f"{self._number(row['turnout_forecast'], 1)}%."
            ),
            "summary": row["interpretation"],
            "confidence_level": confidence,
            "data_origin": datasets,
            "methodological_notes": [
                "Es un forecast estructural interno, no una encuesta ni un resultado observado.",
                "Las hipotesis contextuales estan acotadas y no deben interpretarse como hechos politicos.",
                f"Confianza cuantitativa del modelo: {self._number(row['forecast_confidence'], 1)} sobre 100.",
            ],
        }

    def _data_lookup(self, question: str, municipality_id: str) -> dict:
        party = extract_party(question)
        if not party:
            return self._unsupported(
                "He identificado una consulta de datos, pero necesito una peticion mas concreta con una variable electoral disponible, por ejemplo la fortaleza territorial del PSOE, PP, VOX o CS."
            )
        datasets = ["marts.mv_electoral_behavior", "marts.dim_seccion_display"]
        self.datasets.require("marts.mv_electoral_behavior")
        rows = self.repository.get_party_strength(municipality_id, party)
        if not rows:
            return self._unsupported(f"No encuentro resultados internos suficientes para describir la fortaleza territorial de {party}.")
        strongest = rows[0]
        return {
            "answer": (
                f"La mayor fortaleza territorial observada de {party} en las municipales de 2023 esta en "
                f"{strongest['section']}, con un {self._number(strongest['percentage'], 1)}% de voto valido."
            ),
            "summary": f"Estas son las cinco secciones con mayor porcentaje observado de voto para {party}.",
            "confidence_level": "high",
            "data_origin": datasets,
            "methodological_notes": [
                "Dato observado: resultados de las elecciones municipales de 2023 por seccion.",
                "El ranking describe concentracion territorial del voto; no es una proyeccion futura.",
            ],
            "caveats": ["Esta respuesta es un ranking simple de 2023, no una media historica."],
            "table": AnalystTable(
                title=f"Secciones con mayor voto observado de {party}",
                columns=["Seccion", "Voto valido"],
                rows=[[str(row["section"]), f"{float(row['percentage']):.1f}%"] for row in rows],
            ),
        }

    def _historical_party_average(self, question: str, municipality_id: str, *, include_similarity: bool) -> dict:
        party = extract_party(question)
        if not party:
            return self._unsupported(
                "Para calcular una media historica necesito identificar un partido concreto, por ejemplo PP, PSOE o VOX."
            )

        datasets = [
            "core.resultados_seccion",
            "core.election",
            "core.candidatura_alias",
            "marts.dim_seccion_display",
        ]
        self.datasets.require("core.resultados_seccion")
        ranking = self.repository.get_historical_party_average(municipality_id, party, limit=10)
        elections = self.repository.get_available_elections(municipality_id)

        if not ranking:
            available = self._format_election_list(elections)
            return {
                "answer": (
                    f"No puedo calcular una media historica de {party} porque no encuentro registros normalizados "
                    f"para ese partido en las elecciones cargadas. Elecciones disponibles detectadas: {available}."
                ),
                "summary": "No se ha sustituido la consulta historica por un ranking simple de 2023.",
                "title": f"Media historica de {party} no disponible",
                "confidence_level": "low",
                "data_origin": datasets,
                "methodology": "Busqueda de resultados normalizados por seccion, eleccion y partido canonico.",
                "methodological_notes": [
                    "No se han inferido partidos ausentes.",
                    "No se ha usado informacion externa.",
                ],
                "caveats": ["La disponibilidad depende de los procesos electorales cargados en la base SocTrace."],
            }

        top = ranking[0]
        top_sections = ranking[:5]
        available = self._format_election_list(elections)
        similarity_rows = self.repository.get_section_similarity_profile(
            municipality_id,
            [str(row["section_id"]) for row in top_sections],
        ) if include_similarity else []
        findings = self._build_similarity_findings(similarity_rows) if include_similarity else []
        similarity_sentence = ""
        if include_similarity:
            datasets.extend(
                [
                    "marts.v_population_layer",
                    "marts.v_mapa_age_structure_2023",
                    "marts.v_income_level_layer",
                    "marts.v_land_built_environment",
                    "marts.territorial_intelligence_section_2023",
                ]
            )
            if findings:
                similarity_sentence = (
                    " Al comparar las secciones con mayor media historica con la media municipal, aparecen "
                    f"{len(findings)} patrones descriptivos: "
                    + "; ".join(f"{finding['label']}: {finding['description']}" for finding in findings[:3])
                    + "."
                )
            else:
                similarity_sentence = (
                    " He intentado comparar esas secciones con indicadores socioeconomicos, pero los campos "
                    "disponibles no ofrecen suficientes valores comunes para sostener un perfil descriptivo."
                )

        answer = (
            f"He calculado la media simple del porcentaje de voto de {party} en las elecciones actualmente disponibles, "
            "agrupando los resultados por seccion. "
            f"La seccion con mayor media historica es {top['section_name']}, con una media del "
            f"{self._number(top['average_vote_pct'], 1)}% en {top['number_of_elections_available']} elecciones disponibles."
            f"{similarity_sentence}"
        )

        caveats = [
            "La media historica es una media simple de porcentajes por eleccion; no promedia votos brutos.",
            "Para evitar falsos liderazgos historicos, el ranking exige al menos dos elecciones disponibles por seccion.",
            "La lectura de similitud es descriptiva, no causal.",
            "Solo se incluyen elecciones actualmente cargadas y normalizadas en SocTrace.",
        ]

        return {
            "answer": answer,
            "summary": (
                f"{top['section_name']} lidera la media historica de {party}; el ranking muestra las secciones con "
                "mayor porcentaje medio observado."
            ),
            "title": f"Media historica de voto de {party} por seccion",
            "methodology": (
                "Normalizo etiquetas de partido a una familia canonica, calculo el porcentaje de voto valido por "
                "seccion y eleccion, y despues obtengo una media simple de esos porcentajes por seccion. "
                "Para la similitud, comparo el promedio de las cinco secciones lideres con la media municipal "
                "en indicadores sociales, economicos y territoriales disponibles para 2023."
            ),
            "metrics": [
                {
                    "label": "Seccion lider",
                    "value": str(top["section_name"]),
                    "description": f"{self._number(top['average_vote_pct'], 1)}% de media historica",
                },
                {
                    "label": "Elecciones detectadas",
                    "value": len(elections),
                    "description": available,
                },
                {
                    "label": "Metodo",
                    "value": "Media simple",
                    "description": "Porcentaje de voto valido por eleccion, no votos brutos.",
                },
            ],
            "findings": findings,
            "caveats": caveats,
            "suggested_follow_ups": [
                f"Comparar la media historica de {party} con PSOE y VOX.",
                f"Ver solo elecciones municipales para {party}.",
                "Separar el perfil socioeconomico por costa, urbanizaciones e interior.",
            ],
            "confidence_level": "high" if len(elections) >= 2 else "medium",
            "data_origin": datasets,
            "methodological_notes": [
                "Dato observado: resultados electorales por seccion y candidatura.",
                "La normalizacion agrupa alias equivalentes bajo una etiqueta canonica de partido.",
                "El calculo usa porcentajes de voto valido para evitar sesgos por tamanos de seccion y participacion.",
                f"Elecciones incluidas detectadas: {available}.",
            ],
            "table": AnalystTable(
                title=f"Top secciones por media historica de voto de {party}",
                columns=[
                    "Seccion",
                    "Media",
                    "Mediana",
                    "Min",
                    "Max",
                    "Ultima",
                    "Elecciones",
                    "Tendencia",
                ],
                rows=[
                    [
                        str(row["section_name"]),
                        f"{float(row['average_vote_pct']):.1f}%",
                        f"{float(row['median_vote_pct']):.1f}%",
                        f"{float(row['min_vote_pct']):.1f}%",
                        f"{float(row['max_vote_pct']):.1f}%",
                        f"{float(row['latest_vote_pct']):.1f}%",
                        str(row["number_of_elections_available"]),
                        self._format_trend(row.get("trend_pp")),
                    ]
                    for row in ranking
                ],
            ),
        }

    def _historical_party_dominance_for_section(self, question: str, municipality_id: str) -> dict:
        datasets = [
            "core.resultados_seccion",
            "core.election",
            "core.candidatura_alias",
            "marts.dim_seccion_display",
            "marts.v_mapa_age_structure_2023",
        ]
        self.datasets.require("core.resultados_seccion", "marts.dim_seccion_display")

        section_hint = extract_section_hint(question)
        section = self._resolve_section(section_hint, municipality_id) if section_hint else None
        used_youngest_context = False
        if not section:
            section = self.repository.get_youngest_section(municipality_id)
            used_youngest_context = True

        if not section:
            return self._unsupported("No he podido resolver una seccion para calcular su historico electoral.")

        results = self.repository.get_normalized_election_results(
            municipality_id,
            section_id=str(section["section_id"]),
        )
        if not results:
            return self._unsupported(f"No encuentro resultados electorales normalizados para {section['display_name']}.")

        party_stats: dict[str, dict] = {}
        for row in results:
            party = str(row["party"])
            stats = party_stats.setdefault(
                party,
                {
                    "party": party,
                    "vote_pcts": [],
                    "votes": 0,
                    "first_place_count": 0,
                    "first_year": int(row["election_year"]),
                    "last_year": int(row["election_year"]),
                },
            )
            stats["vote_pcts"].append(float(row["vote_pct"]))
            stats["votes"] += int(row["votes"])
            stats["first_year"] = min(stats["first_year"], int(row["election_year"]))
            stats["last_year"] = max(stats["last_year"], int(row["election_year"]))

        winners_by_election: dict[str, str] = {}
        for row in results:
            election_id = str(row["election_id"])
            current_winner = winners_by_election.get(election_id)
            if current_winner is None:
                winners_by_election[election_id] = str(row["party"])
                continue
            current_row = next(
                item for item in results if str(item["election_id"]) == election_id and str(item["party"]) == current_winner
            )
            if float(row["vote_pct"]) > float(current_row["vote_pct"]):
                winners_by_election[election_id] = str(row["party"])

        for winner in winners_by_election.values():
            if winner in party_stats:
                party_stats[winner]["first_place_count"] += 1

        ranking = sorted(
            (
                {
                    **stats,
                    "average_vote_pct": sum(stats["vote_pcts"]) / len(stats["vote_pcts"]),
                    "elections_included": len(stats["vote_pcts"]),
                }
                for stats in party_stats.values()
                if stats["vote_pcts"]
            ),
            key=lambda item: (-item["average_vote_pct"], -item["first_place_count"], -item["votes"], item["party"]),
        )
        top = ranking[0]
        context_note = (
            "Como la pregunta llega sin una seccion explicita, uso la seccion mas joven identificada en 2023 como contexto. "
            if used_youngest_context
            else ""
        )

        return {
            "answer": (
                f"{context_note}En {section['display_name']}, el partido historicamente mas fuerte entre las elecciones "
                f"disponibles es {top['party']}, con una media del {self._number(top['average_vote_pct'], 1)}% "
                f"del voto valido en {top['elections_included']} observaciones y {top['first_place_count']} primeras posiciones."
            ),
            "summary": (
                f"Historico electoral por partido para {section['display_name']}; el ranking ordena por porcentaje medio, "
                "victorias y votos totales."
            ),
            "title": f"Historico electoral de {section['display_name']}",
            "methodology": (
                "Agrupo resultados normalizados por partido canonico en la seccion, calculo la media simple del porcentaje "
                "de voto valido por eleccion y cuento en cuantas elecciones cada partido fue primera fuerza."
            ),
            "confidence_level": "high" if top["elections_included"] >= 2 else "medium",
            "data_origin": datasets,
            "methodological_notes": [
                "Dato observado: resultados electorales normalizados por seccion, eleccion y partido.",
                "La comparacion usa porcentaje de voto valido, no votos absolutos.",
                "Si no se indica seccion, se toma la seccion mas joven de Mijas en 2023 como contexto conversacional.",
            ],
            "caveats": ["Solo se incluyen elecciones actualmente cargadas y normalizadas en SocTrace."],
            "suggested_follow_ups": [
                f"Ver eleccion por eleccion para {top['party']} en {section['display_name']}.",
                "Comparar esta seccion con otra zona joven.",
            ],
            "table": AnalystTable(
                title=f"Partidos historicamente mas fuertes en {section['display_name']}",
                columns=["Partido", "Media voto valido", "Primeras posiciones", "Votos totales", "Observaciones", "Periodo"],
                rows=[
                    [
                        str(row["party"]),
                        f"{float(row['average_vote_pct']):.1f}%",
                        str(row["first_place_count"]),
                        self._number(int(row["votes"])),
                        str(row["elections_included"]),
                        f"{row['first_year']}-{row['last_year']}",
                    ]
                    for row in ranking[:10]
                ],
            ),
        }

    def _party_performance_by_section(self, question: str, municipality_id: str) -> dict:
        party = extract_party(question)
        section_hint = extract_section_hint(question)
        direction = extract_metric_direction(question)
        datasets = [
            "core.resultados_seccion",
            "core.election",
            "core.candidatura_alias",
            "marts.dim_seccion_display",
        ]
        self.datasets.require("core.resultados_seccion", "marts.dim_seccion_display")

        section = self._resolve_section(section_hint, municipality_id) if section_hint else None
        if not section:
            return {
                "answer": "No he podido identificar la seccion a la que te refieres. Prueba con el numero de seccion o con el nombre tal como aparece en el mapa.",
                "summary": "La consulta no se ha sustituido por un ranking global.",
                "title": "Seccion no identificada",
                "confidence_level": "low",
                "data_origin": ["marts.dim_seccion_display"],
                "methodology": "Intento resolver la seccion por id interno, numero visible o nombre comercial de la seccion.",
                "methodological_notes": ["No se ha devuelto un ranking municipal porque la pregunta es especifica de una seccion."],
                "caveats": ["Indica, por ejemplo, 'seccion 36' o 'Sierrezuela'."],
            }

        if not party:
            return {
                "answer": f"He identificado {section['display_name']}, pero no el partido. Indica el partido que quieres analizar.",
                "summary": "Falta la entidad partido para calcular la evolucion electoral.",
                "title": "Partido no identificado",
                "confidence_level": "low",
                "data_origin": ["marts.dim_seccion_display"],
                "methodological_notes": ["No se ha inferido un partido ausente."],
            }

        results = self.repository.get_normalized_election_results(
            municipality_id,
            party=party,
            section_id=str(section["section_id"]),
        )
        if len(results) < 2:
            available = self._format_election_list(results)
            return {
                "answer": (
                    f"Para {section['display_name']} solo encuentro datos de {len(results)} eleccion para {party}. "
                    "No puedo determinar el peor o mejor resultado historico con una unica observacion."
                ),
                "summary": "No hay suficientes observaciones multi-eleccion para esta seccion y partido.",
                "title": f"Evolucion de {party} en {section['display_name']}",
                "confidence_level": "low",
                "data_origin": datasets,
                "methodology": "Filtro resultados normalizados por partido canonico y seccion, usando porcentaje de voto valido.",
                "methodological_notes": [
                    f"Elecciones encontradas: {available}.",
                    "No se comparan votos absolutos porque censo y participacion cambian entre elecciones.",
                ],
                "caveats": ["Se ampliara cuando haya mas procesos normalizados para esa seccion."],
            }

        sorted_by_pct = sorted(results, key=lambda row: float(row["vote_pct"]))
        chronological = sorted(results, key=lambda row: (int(row["election_year"]), int(row.get("election_month") or 0), int(row["election_id"])))
        target = sorted_by_pct[-1] if direction == "max" else sorted_by_pct[0]
        if direction == "trend":
            target = chronological[-1]
        section_average = sum(float(row["vote_pct"]) for row in results) / len(results)
        delta = float(target["vote_pct"]) - section_average
        target_label = self._election_label(target)
        direction_label = {
            "min": "peor porcentaje",
            "max": "mejor porcentaje",
            "trend": "ultimo porcentaje disponible",
        }[direction]
        verb = {
            "min": "fue",
            "max": "fue",
            "trend": "es",
        }[direction]
        answer = (
            f"En {section['display_name']}, el {direction_label} de voto del {party} entre las elecciones disponibles "
            f"{verb} en {target_label}, con un {self._number(float(target['vote_pct']), 1)}% del voto valido. "
            f"Ese resultado esta {self._format_signed_points(delta)} de la media del {party} en esa seccion, "
            f"que es {self._number(section_average, 1)}%."
        )
        if direction == "trend":
            first = chronological[0]
            latest = chronological[-1]
            trend_delta = float(latest["vote_pct"]) - float(first["vote_pct"])
            answer += (
                f" Entre la primera eleccion disponible ({self._election_label(first)}) y la ultima "
                f"({self._election_label(latest)}), la variacion es {self._format_signed_points(trend_delta)}."
            )

        ranking_rows = sorted_by_pct if direction == "min" else list(reversed(sorted_by_pct))
        return {
            "answer": answer,
            "summary": (
                f"Analisis de {party} en {section['display_name']} a traves de {len(results)} elecciones disponibles."
            ),
            "title": f"{party} en {section['display_name']} por eleccion",
            "methodology": (
                "Filtro los resultados electorales normalizados por seccion y partido canonico, comparo porcentajes "
                "de voto valido y calculo la media simple de la seccion para ese partido."
            ),
            "metrics": [
                {
                    "label": "Resultado seleccionado",
                    "value": f"{self._number(float(target['vote_pct']), 1)}%",
                    "description": target_label,
                },
                {
                    "label": "Media seccional",
                    "value": f"{self._number(section_average, 1)}%",
                    "description": f"Media simple de {len(results)} elecciones disponibles.",
                },
                {
                    "label": "Diferencia",
                    "value": self._format_signed_points(delta),
                    "description": "Respecto a la media de la seccion para ese partido.",
                },
            ],
            "confidence_level": "high",
            "data_origin": datasets,
            "methodological_notes": [
                "Dato observado: resultados normalizados por seccion, eleccion y partido.",
                "Comparo porcentajes de voto valido, no votos absolutos.",
                f"Elecciones usadas: {self._format_election_list(results)}.",
            ],
            "caveats": [
                "El calculo usa las elecciones actualmente disponibles en el dataset.",
                "Los votos absolutos se muestran como referencia, pero la comparacion se ordena por porcentaje de voto valido.",
            ],
            "suggested_follow_ups": [
                f"Comparar {party} con PSOE y VOX en {section['display_name']}.",
                f"Ver el mismo analisis solo para elecciones municipales en {section['display_name']}.",
            ],
            "table": AnalystTable(
                title=f"Resultados de {party} en {section['display_name']}",
                columns=["Eleccion", "Voto valido", "Votos", "Votos validos", "Diferencia vs media"],
                rows=[
                    [
                        self._election_label(row),
                        f"{float(row['vote_pct']):.1f}%",
                        self._number(int(row["votes"])),
                        self._number(int(row["valid_votes"])),
                        self._format_signed_points(float(row["vote_pct"]) - section_average),
                    ]
                    for row in ranking_rows
                ],
            ),
        }

    def _turnout_comparison(self, municipality_id: str) -> dict:
        datasets = ["marts.mv_electoral_behavior"]
        self.datasets.require(*datasets)
        rows = self.repository.get_turnout_comparison(municipality_id)
        values = {int(row["year"]): float(row["turnout"]) for row in rows}
        if 2019 not in values or 2023 not in values:
            return self._unsupported("Faltan datos observados para comparar la participacion municipal de 2019 y 2023.")
        difference = values[2023] - values[2019]
        return {
            "answer": f"La participacion municipal paso del {values[2019]:.1f}% en 2019 al {values[2023]:.1f}% en 2023: {difference:+.1f} puntos porcentuales.",
            "summary": "La comparacion usa votos emitidos y censo agregados para el conjunto de Mijas.",
            "confidence_level": "high",
            "data_origin": datasets,
            "methodological_notes": ["Dato observado. La diferencia se expresa en puntos porcentuales, no en porcentaje relativo."],
            "table": AnalystTable(
                title="Participacion municipal observada",
                columns=["Eleccion", "Participacion"],
                rows=[[str(year), f"{value:.1f}%"] for year, value in sorted(values.items())],
            ),
            "chart_spec": AnalystChartSpec(
                kind="bar",
                title="Participacion municipal observada",
                data=[{"year": year, "turnout": value} for year, value in sorted(values.items())],
            ),
        }

    def _methodology(self) -> dict:
        methodology = self.pack.load_municipality_context("mijas").documents["methodology.md"]
        return {
            "answer": "SocTrace separa datos observados, indicadores estimados y forecast. El forecast municipal es una linea base estructural interna: no es una encuesta y no afirma que una hipotesis politica vaya a ocurrir.",
            "summary": "Las respuestas deben explicitar incertidumbre, confianza y limites de interpretacion.",
            "confidence_level": "high",
            "data_origin": ["municipality_packs/mijas/methodology.md"],
            "methodological_notes": [line.removeprefix("- ").strip() for line in methodology.splitlines() if line.startswith("- ")],
        }

    def _strategic(self, municipality_id: str) -> dict:
        self.pack.load_municipality_context("mijas").documents["political_context_structured.md"]
        forecast = self._forecast(municipality_id)
        forecast["answer"] = "La lectura estrategica disponible debe tratarse como una orientacion analitica, no como un hecho politico. " + forecast["answer"]
        forecast["data_origin"] = [*forecast["data_origin"], "municipality_packs/mijas/political_context_structured.md"]
        forecast["methodological_notes"].append("Las hipotesis territoriales sirven para formular preguntas y priorizar validacion de campo.")
        return forecast

    def _unsupported(self, answer: str) -> dict:
        return {
            "answer": answer,
            "summary": "La respuesta se limita a la informacion interna aprobada disponible.",
            "confidence_level": "low",
            "data_origin": [],
            "methodological_notes": ["No se han inferido datos ausentes ni se ha usado informacion externa."],
            "caveats": ["La consulta no se ha degradado a una respuesta simple no equivalente."],
        }

    def _build_similarity_findings(self, rows: list[dict]) -> list[dict]:
        if not rows:
            return []

        variable_specs = [
            ("individual_income", "Renta individual", "euros", "municipality_individual_income"),
            ("household_income", "Renta del hogar", "euros", "municipality_household_income"),
            ("average_age", "Edad media", "number", "municipality_average_age"),
            ("over_65_pct", "Poblacion mayor de 65", "percent_ratio", "municipality_over_65_pct"),
            ("under_30_pct", "Poblacion menor de 30", "percent_ratio", "municipality_under_30_pct"),
            ("population_density", "Densidad de poblacion", "number", "municipality_population_density"),
            ("parcel_density", "Densidad parcelaria", "number", "municipality_parcel_density"),
            ("building_intensity", "Intensidad edificatoria", "number", "municipality_building_intensity"),
            ("urban_intensity_index", "Intensidad urbana", "index", "municipality_urban_intensity_index"),
            ("market_reference_m2", "Referencia de mercado residencial", "euros_m2", "municipality_market_reference_m2"),
            ("market_pressure_index", "Presion de mercado", "index", "municipality_market_pressure_index"),
        ]

        findings: list[dict] = []
        for key, label, value_type, municipal_key in variable_specs:
            group_values = [float(row[key]) for row in rows if row.get(key) is not None]
            municipal_values = [float(row[municipal_key]) for row in rows if row.get(municipal_key) is not None]
            if not group_values or not municipal_values:
                continue

            group_average = sum(group_values) / len(group_values)
            municipal_average = municipal_values[0]
            if municipal_average == 0:
                continue

            difference = group_average - municipal_average
            relative_difference = difference / abs(municipal_average)
            if abs(relative_difference) < 0.05:
                pattern = "similar a la media municipal"
            elif relative_difference > 0:
                pattern = "superior a la media municipal"
            else:
                pattern = "inferior a la media municipal"

            above_count = sum(1 for value in group_values if value > municipal_average)
            evidence = (
                f"{above_count} de {len(group_values)} secciones estan por encima de la media municipal; "
                f"promedio del grupo {self._format_value(group_average, value_type)} frente a "
                f"{self._format_value(municipal_average, value_type)} en Mijas."
            )
            findings.append(
                {
                    "label": label,
                    "description": pattern,
                    "evidence": evidence,
                }
            )

        priority = {
            "Renta individual": 0,
            "Renta del hogar": 1,
            "Edad media": 2,
            "Poblacion mayor de 65": 3,
            "Densidad de poblacion": 4,
            "Intensidad urbana": 5,
            "Referencia de mercado residencial": 6,
        }
        return sorted(findings, key=lambda item: priority.get(item["label"], 99))[:6]

    def _format_election_list(self, elections: list[dict]) -> str:
        if not elections:
            return "ninguna eleccion normalizada detectada"
        labels = [
            f"{row['election_type']} {row['election_year']}"
            + (f"/{row['election_month']}" if row.get("election_month") else "")
            for row in elections
        ]
        return ", ".join(labels)

    def _format_trend(self, value) -> str:
        if value is None:
            return "No calculable"
        number = float(value)
        if abs(number) < 0.5:
            return "Estable"
        return f"{number:+.1f} pp"

    def _resolve_section(self, section_hint: str | None, municipality_id: str) -> dict | None:
        if not section_hint:
            return None

        hint = normalize(section_hint)
        sections = self.repository.get_section_lookup(municipality_id)
        section_id_match = re.search(r"\b29\d{8}\b", hint)
        if section_id_match:
            section_id = section_id_match.group(0)
            return next((section for section in sections if str(section["section_id"]) == section_id), None)

        if hint.isdigit():
            requested_number = str(int(hint)).zfill(2)
            return next(
                (
                    section
                    for section in sections
                    if str(section.get("section_number") or "").zfill(2) == requested_number
                    or str(section["section_id"]).endswith(requested_number)
                ),
                None,
            )

        hint_tokens = self._meaningful_tokens(hint)
        best_match: tuple[int, dict] | None = None
        for section in sections:
            search_blob = normalize(
                " ".join(
                    str(value)
                    for value in (
                        section.get("display_name"),
                        section.get("nombre_barrio"),
                        section.get("zona_macro"),
                        section.get("section_number"),
                        section.get("section_id"),
                    )
                    if value
                )
            )
            if hint and hint in search_blob:
                score = 100
            else:
                score = sum(1 for token in hint_tokens if token in search_blob)
            if score and (best_match is None or score > best_match[0]):
                best_match = (score, section)

        if not best_match:
            return None
        score, section = best_match
        return section if score >= max(1, min(2, len(hint_tokens))) else None

    @staticmethod
    def _meaningful_tokens(text: str) -> list[str]:
        stopwords = {"la", "el", "las", "los", "de", "del", "en", "seccion", "section"}
        return [
            token
            for token in re.findall(r"[a-z0-9]+", normalize(text))
            if token not in stopwords and len(token) > 1
        ]

    def _election_label(self, row: dict) -> str:
        label = f"{row['election_type']} {row['election_year']}"
        if row.get("election_month"):
            label += f"/{row['election_month']}"
        return label

    def _format_signed_points(self, value: float) -> str:
        if abs(value) < 0.05:
            return "en linea con la media"
        direction = "por encima" if value > 0 else "por debajo"
        return f"{self._number(abs(value), 1)} puntos {direction}"

    def _format_value(self, value: float, value_type: str) -> str:
        if value_type == "euros":
            return f"{self._number(value, 0)} euros"
        if value_type == "euros_m2":
            return f"{self._number(value, 0)} euros/m2"
        if value_type == "percent_ratio":
            return f"{self._number(value * 100 if value <= 1 else value, 1)}%"
        if value_type == "index":
            return f"{self._number(value, 1)}/100"
        return self._number(value, 1)

    @staticmethod
    def _number(value: float | int | None, decimals: int = 0) -> str:
        if value is None:
            return "no disponible"
        return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def get_local_analyst_service(session: Session = Depends(get_db_session)) -> LocalAnalystService:
    return LocalAnalystService(session)
