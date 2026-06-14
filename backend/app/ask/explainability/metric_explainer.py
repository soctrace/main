from __future__ import annotations

from app.ask.explainability.schemas import MetricExplanation


METRIC_EXPLANATIONS: dict[str, MetricExplanation] = {
    "population_total": MetricExplanation(metric="population_total", label="Población total", plain_definition="Número de personas empadronadas o estimadas en una sección o municipio.", interpretation="Sirve para dimensionar el peso territorial de una zona.", caveat="No equivale necesariamente a población con derecho a voto."),
    "population_density": MetricExplanation(metric="population_density", label="Densidad de población", plain_definition="Relación entre población y superficie.", interpretation="Ayuda a distinguir zonas más compactas de zonas más dispersas."),
    "population_under_30": MetricExplanation(metric="population_under_30", label="Población joven", plain_definition="Personas menores de 30 años.", interpretation="Indica presencia relativa de población joven y posibles demandas de vivienda, empleo, movilidad o servicios."),
    "population_under_30_pct": MetricExplanation(metric="population_under_30_pct", label="Peso de población joven", plain_definition="Porcentaje de residentes menores de 30 años sobre la población total de la sección.", interpretation="Permite comparar juventud relativa entre zonas de distinto tamaño."),
    "population_over_65": MetricExplanation(metric="population_over_65", label="Población senior", plain_definition="Población de 65 años o más.", interpretation="Sirve como aproximación demográfica a población senior o jubilada.", caveat="No equivale exactamente a pensionistas reales."),
    "population_over_65_pct": MetricExplanation(metric="population_over_65_pct", label="Peso de población mayor", plain_definition="Porcentaje de residentes de 65 años o más sobre la población total de la sección.", interpretation="Permite comparar envejecimiento relativo entre zonas de distinto tamaño."),
    "average_age": MetricExplanation(metric="average_age", label="Edad media", plain_definition="Promedio de edad de la población residente.", interpretation="Resume si una zona tiene perfil más joven o más envejecido."),
    "population_growth_abs": MetricExplanation(metric="population_growth_abs", label="Crecimiento absoluto", plain_definition="Cambio en número de habitantes entre dos años.", interpretation="Mide cuántas personas gana o pierde una zona."),
    "population_growth_pct": MetricExplanation(metric="population_growth_pct", label="Crecimiento porcentual", plain_definition="Cambio relativo de población entre dos años.", interpretation="Permite comparar crecimiento entre zonas de distinto tamaño."),
    "vote_pct": MetricExplanation(metric="vote_pct", label="Porcentaje de voto", plain_definition="Porcentaje de votos válidos obtenidos por un partido en una elección.", interpretation="Mide fortaleza electoral relativa en una sección."),
    "left_bloc_pct": MetricExplanation(metric="left_bloc_pct", label="Voto de izquierdas", plain_definition="Peso agregado de candidaturas del bloque progresista.", interpretation="Ayuda a identificar secciones con inclinación electoral progresista."),
    "right_bloc_pct": MetricExplanation(metric="right_bloc_pct", label="Voto de derechas", plain_definition="Peso agregado de candidaturas del bloque conservador.", interpretation="Ayuda a identificar secciones con inclinación electoral conservadora."),
    "local_vote_pct": MetricExplanation(metric="local_vote_pct", label="Voto localista", plain_definition="Peso de candidaturas de ámbito local.", interpretation="Puede señalar arraigo territorial o sensibilidad a liderazgos municipales."),
    "national_vote_pct": MetricExplanation(metric="national_vote_pct", label="Voto a partidos nacionales", plain_definition="Peso de candidaturas de ámbito estatal.", interpretation="Indica cuánto pesa la lógica nacional frente a la local."),
    "participation_pct": MetricExplanation(metric="participation_pct", label="Participación", plain_definition="Porcentaje del censo que participó en la elección.", interpretation="Mide capacidad de movilización electoral de una zona."),
    "abstention_pct": MetricExplanation(metric="abstention_pct", label="Abstención", plain_definition="Porcentaje de personas con derecho a voto que no participaron en una elección.", interpretation="Una abstención alta puede señalar desmovilización, desconexión política o menor capacidad de activación electoral."),
    "margin_pct": MetricExplanation(metric="margin_pct", label="Margen electoral", plain_definition="Diferencia entre la primera y la segunda fuerza.", interpretation="Cuanto menor es el margen, más competitiva es la sección."),
    "winner_party": MetricExplanation(metric="winner_party", label="Partido ganador", plain_definition="Candidatura con más votos en una sección.", interpretation="Resume la primera fuerza territorial."),
    "historical_vote_avg": MetricExplanation(metric="historical_vote_avg", label="Media histórica de voto", plain_definition="Promedio de voto de un partido en varias elecciones.", interpretation="Mide fortaleza estructural más allá de una sola elección."),
    "electoral_volatility": MetricExplanation(metric="electoral_volatility", label="Volatilidad electoral", plain_definition="Variación del apoyo electoral entre elecciones.", interpretation="Una volatilidad alta indica más margen de cambio o inestabilidad territorial."),
    "electoral_competitiveness": MetricExplanation(metric="electoral_competitiveness", label="Competitividad electoral", plain_definition="Nivel de disputa entre candidaturas.", interpretation="Zonas muy competitivas pueden ser prioritarias para campaña."),
    "mobilizable_abstention": MetricExplanation(metric="mobilizable_abstention", label="Abstención movilizable", plain_definition="Índice territorial que combina abstención, peso electoral, competitividad y afinidad política cuando existe contexto.", interpretation="Ayuda a priorizar zonas donde una estrategia de movilización podría ser más relevante.", caveat="No predice voto individual ni garantiza conversión electoral."),
    "income_individual": MetricExplanation(metric="income_individual", label="Renta individual", plain_definition="Ingreso medio individual estimado.", interpretation="Aproxima nivel socioeconómico personal de una zona."),
    "income_household": MetricExplanation(metric="income_household", label="Renta del hogar", plain_definition="Ingreso medio por hogar.", interpretation="Aproxima capacidad económica familiar."),
    "salary_share": MetricExplanation(metric="salary_share", label="Peso salarial", plain_definition="Peso relativo de ingresos procedentes de salarios.", interpretation="Ayuda a caracterizar zonas con mayor dependencia de empleo asalariado."),
    "pension_share": MetricExplanation(metric="pension_share", label="Peso de pensiones", plain_definition="Peso relativo de ingresos procedentes de pensiones.", interpretation="Aproxima presencia económica de población pensionista."),
    "unemployment_share": MetricExplanation(metric="unemployment_share", label="Peso del desempleo", plain_definition="Peso relativo de prestaciones por desempleo.", interpretation="Puede señalar vulnerabilidad laboral."),
    "market_price_estimated_m2": MetricExplanation(metric="market_price_estimated_m2", label="Precio inmobiliario estimado", plain_definition="Valor estimado por metro cuadrado de mercado.", interpretation="Permite detectar presión o atractivo inmobiliario."),
    "estimated_cadastral_value_m2": MetricExplanation(metric="estimated_cadastral_value_m2", label="Valor catastral estimado", plain_definition="Valor catastral aproximado por metro cuadrado.", interpretation="Aproxima valoración administrativa del parque inmobiliario."),
    "market_to_cadastral_ratio": MetricExplanation(metric="market_to_cadastral_ratio", label="Relación mercado-catastro", plain_definition="Relación entre valor de mercado estimado y valor catastral estimado.", interpretation="Ayuda a detectar margen relativo entre valoración de mercado y referencia catastral.", caveat="Es una aproximación territorial, no una tasación individual."),
    "residential_pressure_index": MetricExplanation(metric="residential_pressure_index", label="Presión residencial", plain_definition="Índice de tensión o intensidad residencial.", interpretation="Ayuda a detectar zonas con mayor presión de vivienda."),
    "building_intensity": MetricExplanation(metric="building_intensity", label="Intensidad edificatoria", plain_definition="Nivel de edificación sobre el suelo disponible.", interpretation="Señala zonas más densamente construidas."),
    "parcel_density": MetricExplanation(metric="parcel_density", label="Densidad parcelaria", plain_definition="Concentración de parcelas en el territorio.", interpretation="Describe estructura urbana y fragmentación del suelo."),
    "built_footprint": MetricExplanation(metric="built_footprint", label="Huella construida", plain_definition="Superficie ocupada por edificaciones.", interpretation="Mide intensidad física de ocupación urbana."),
}


class MetricExplainer:
    def explain(self, metric: str | None) -> MetricExplanation | None:
        if not metric:
            return None
        return METRIC_EXPLANATIONS.get(metric)

    def explain_many(self, metrics: list[str]) -> list[MetricExplanation]:
        return [explanation for metric in metrics if (explanation := self.explain(metric))]
