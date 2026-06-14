# Ask SocTrace Test Catalog Audit

Fecha: 2026-06-09.

Estados visibles del MVP: `Disponible` y `Próximamente`. Los estados internos `supported`, `beta` y `pending` no se exponen en la UI.

Resumen: 124 de 158 consultas visibles quedan como `Disponible` (78.5%).

| Category | Question | Current status | Tool available? | Semantic mapping available? | Dataset available? | Can execute now? | Recommended status | Reason |
|---|---|---:|---:|---:|---:|---:|---|---|
| Demografia - Poblacion | ¿Cuál es la sección con mayor población? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Poblacion | ¿Cuál es la sección con menor población? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Poblacion | ¿Qué secciones superan los 5.000 habitantes? | legacy | filter_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Poblacion | ¿Cuál es la población total de Mijas? | legacy | aggregate_municipality | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Poblacion | ¿Cómo ha evolucionado la población desde 2021? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Poblacion | ¿Qué zonas han crecido más? | legacy | population_growth | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Cuál es la sección más joven? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Cuál es la más envejecida? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Dónde viven más menores de 18 años? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Dónde viven más personas mayores de 65 años? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué porcentaje de la población tiene menos de 30 años? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué secciones tienen más población en edad laboral? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Siempre ha sido la sección más joven? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué sección ha rejuvenecido más desde 2021? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué sección ha envejecido más desde 2021? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué sección ha envejecido más? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué secciones tienen más menores de 30 años? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué secciones tienen más mayores de 65 años? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué porcentaje de población joven tiene cada sección? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué porcentaje de población jubilada tiene cada sección? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Edad | ¿Qué zonas tienen mayor dependencia demográfica? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Cuántas personas aproximadamente tendrán 18 años en 2027? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Cuántas personas tendrán 18 años en 2027? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Qué secciones tendrán más nuevos votantes en 2027? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Cuántas personas tenían entre 18 y 22 años en 2023? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Cuántas personas entre 18 y 35 años viven en Riviera Sur? | legacy | age_cohort_projection | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Qué secciones concentran más jóvenes? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Qué secciones concentran más población joven? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Qué secciones concentran más jubilados? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Demografia - Cohortes | ¿Cuántas personas mayores de 65 años viven en Mijas? | legacy | aggregate_municipality | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana el PP siempre? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana siempre el PP? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana el PSOE siempre? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana siempre el PSOE? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana VOX siempre? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Dónde gana siempre VOX? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es el partido históricamente dominante en cada sección? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Qué partido domina históricamente en Riviera Sur? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Qué partido es históricamente más fuerte en la sección más joven? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Qué partido domina la sección más joven? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Qué partido domina la sección más envejecida? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es la sección más favorable al PP? | legacy | party_strength | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es la más favorable al PSOE? | legacy | party_strength | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es la más favorable a VOX? | legacy | party_strength | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es la media histórica de voto del PP? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Partido dominante | ¿Cuál es la media histórica de voto del PSOE? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Participacion | ¿Qué sección tiene más abstención? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Participacion | ¿Cuál tiene menos abstención? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Participacion | ¿Dónde vota más la gente? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Participacion | ¿Dónde vota menos la gente? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Participacion | ¿Qué zonas han reducido más la participación? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Evolucion | ¿Qué secciones cambiaron más entre 2019 y 2023? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2. |
| Electoral - Evolucion | ¿Dónde perdió más apoyo el PSOE? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2. |
| Electoral - Evolucion | ¿Dónde ganó más apoyo el PP? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2. |
| Electoral - Evolucion | ¿Dónde creció más VOX? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2. |
| Electoral - Evolucion | ¿Dónde aparecen más partidos locales? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2. |
| Electoral - Competitividad | ¿Cuáles son las secciones más disputadas? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Dónde hay empate técnico entre PP y PSOE? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Dónde tiene más margen de victoria el partido ganador? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿En qué sección gana con más diferencia el PSOE? | legacy | party_strength | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿En qué sección gana con más diferencia el PP? | legacy | party_strength | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Cuáles son las secciones más competitivas? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Qué secciones son más volátiles electoralmente? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Qué secciones son más conservadoras? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Electoral - Competitividad | ¿Qué secciones son más progresistas? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Consultoria politica - Movilizacion | ¿Dónde debería concentrar esfuerzos el PSOE? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires behavioral mobilization model. |
| Consultoria politica - Movilizacion | ¿Dónde debería concentrar esfuerzos el PP? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires behavioral mobilization model. |
| Consultoria politica - Movilizacion | ¿Qué secciones tienen más abstencionistas potenciales? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires behavioral mobilization model. |
| Consultoria politica - Movilizacion | ¿Dónde hay más jóvenes que no votaron? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires behavioral mobilization model. |
| Consultoria politica - Movilizacion | ¿Qué secciones combinan alta abstención y mucho voto de izquierdas? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Consultoria politica - Movilizacion | ¿Qué secciones combinan alta abstención y mucho voto de derechas? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Consultoria politica - Segmentacion | ¿Dónde vive el votante medio del PP? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires voter profile/segmentation model. |
| Consultoria politica - Segmentacion | ¿Dónde vive el votante medio del PSOE? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires voter profile/segmentation model. |
| Consultoria politica - Segmentacion | ¿Qué características tienen las secciones donde gana VOX? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires voter profile/segmentation model. |
| Consultoria politica - Segmentacion | ¿Qué secciones son más sensibles a una campaña de movilización? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires voter profile/segmentation model. |
| Consultoria politica - Oportunidades | ¿Cuáles son las mejores secciones para ganar un concejal adicional? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires campaign optimization model. |
| Consultoria politica - Oportunidades | ¿Dónde sería más eficiente invertir 10.000 € en campaña? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires campaign optimization model. |
| Consultoria politica - Oportunidades | ¿Qué secciones presentan más indecisión estructural? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires campaign optimization model. |
| Sociologia - Estructura social | ¿Qué secciones tienen más jóvenes y menos renta? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Estructura social | ¿Qué secciones tienen más mayores y más renta? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Estructura social | ¿Dónde existe mayor polarización demográfica? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Estructura social | ¿Qué zonas son más homogéneas? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Vulnerabilidad | ¿Qué secciones presentan más vulnerabilidad social? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Vulnerabilidad | ¿Qué zonas combinan envejecimiento y baja renta? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Vulnerabilidad | ¿Dónde hay más riesgo de exclusión social? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Vulnerabilidad | ¿Qué secciones requieren más servicios públicos? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Cohesion | ¿Qué zonas parecen más cohesionadas socialmente? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Sociologia - Cohesion | ¿Qué zonas muestran perfiles más diversos? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones son más estables? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones son más volátiles? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones cambian de partido ganador según la elección? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Estabilidad electoral | ¿Dónde existen patrones electorales persistentes? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Comportamiento politico | ¿La juventud vota más a la izquierda? | legacy | correlation_analysis | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Comportamiento politico | ¿La renta alta favorece al PP? | legacy | correlation_analysis | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Comportamiento politico | ¿Existe relación entre abstención y renta? | legacy | correlation_analysis | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Ciencia politica - Comportamiento politico | ¿Existe relación entre edad y participación? | legacy | correlation_analysis | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Cuál es la sección más rica? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Cuál es la más pobre? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué secciones tienen mayor renta media? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué secciones tienen menor renta media? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué secciones tienen mayor renta? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué secciones tienen menor renta? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué zonas combinan renta alta y población joven? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué zonas combinan renta baja y envejecimiento? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Renta | ¿Qué zonas combinan renta baja y abstención elevada? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Desigualdad | ¿Qué zonas muestran mayor desigualdad? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Desigualdad | ¿Dónde existe más diferencia entre renta individual y renta del hogar? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Desarrollo | ¿Qué zonas tienen mejor perfil económico? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Economia - Desarrollo | ¿Qué zonas muestran señales de vulnerabilidad económica? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué secciones tienen mayor valor inmobiliario? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué zonas tienen mayor valor inmobiliario? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué secciones tienen menor valor inmobiliario? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Dónde está el mercado más tensionado? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Dónde están las oportunidades inmobiliarias? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué zonas muestran mejor oportunidad inmobiliaria? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué secciones tienen mayor presión residencial? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Mercado | ¿Qué secciones son consideradas zona prime? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Construccion | ¿Qué zonas tienen mayor intensidad edificatoria? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Construccion | ¿Qué zonas tienen más presión urbanística? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Construccion | ¿Dónde se concentra más superficie construida? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Inversion | ¿Qué zonas combinan renta alta y valor inmobiliario alto? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Inversion | ¿Qué zonas parecen infravaloradas? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Inmobiliario - Inversion | ¿Qué zonas tienen mayor potencial de revalorización? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Estadistica - Rankings | Ordena las secciones por población. | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Estadistica - Rankings | Ordena las secciones por renta. | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Estadistica - Rankings | Ordena las secciones por edad media. | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Estadistica - Rankings | Ordena las secciones por abstención. | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Estadistica - Desviaciones | ¿Qué secciones están por encima de la media? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Estadistica - Desviaciones | ¿Qué secciones son outliers? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Estadistica - Desviaciones | ¿Qué variable presenta más dispersión? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Estadistica - Distribuciones | ¿Cómo se distribuye la renta? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Estadistica - Distribuciones | ¿Cómo se distribuye la edad? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Estadistica - Distribuciones | ¿Cómo se distribuye la abstención? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con la abstención? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con el voto al PP? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con el voto al PSOE? | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Clustering | Agrupa secciones similares. | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires dedicated clustering/ML models. |
| Data Science - Clustering | ¿Qué secciones se parecen a Riviera Sur? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires dedicated clustering/ML models. |
| Data Science - Clustering | ¿Qué secciones tienen perfiles equivalentes? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires dedicated clustering/ML models. |
| Data Science - Scores | Crea un índice de vulnerabilidad. | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Scores | Crea un índice de oportunidad electoral. | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Scores | Crea un índice de presión inmobiliaria. | legacy | No | Parcial/No | Parcial | No | Próximamente | No reliable deterministic tool recipe exposed for MVP yet. |
| Data Science - Scores | ¿Qué zonas concentran más población y crecimiento? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Data Science - Scores | ¿Qué zonas combinan juventud y crecimiento? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Data Science - Scores | ¿Qué secciones presentan mejores indicadores territoriales? | legacy | cross_metric_ranking | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Data Science - Prediccion | ¿Qué secciones podrían aumentar la abstención? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires probabilistic forecasting or predictive modelling. |
| Data Science - Prediccion | ¿Qué secciones podrían cambiar de ganador? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires probabilistic forecasting or predictive modelling. |
| Data Science - Prediccion | ¿Qué secciones podrían crecer más demográficamente? | legacy | No | Parcial/No | Parcial | No | Próximamente | Requires probabilistic forecasting or predictive modelling. |
| Conversacional - Contexto 1 | ¿Cuál es la sección más joven? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 1 | ¿Siempre ha sido la más joven? | legacy | compare_years | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 1 | ¿Qué partido es históricamente más fuerte allí? | legacy | historical_party_average | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 1 | ¿Y qué renta tiene? | legacy | section_profile | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 1 | ¿Está por encima o por debajo de la media de Mijas? | legacy | filter_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 2 | ¿Dónde gana siempre el PP? | legacy | persistent_winner | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 2 | ¿Cuál de esas secciones tiene más población? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 2 | ¿Y cuál es la más joven? | legacy | rank_sections | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
| Conversacional - Contexto 2 | ¿Qué partido queda segundo en ella? | legacy | section_profile | Sí | Sí | Sí | Disponible | Tool Layer v2 executable with current Mijas agent_* data. |
