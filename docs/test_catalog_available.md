# Ask SocTrace Available Test Catalog

Fecha: 2026-06-09.

Catálogo interno de consultas marcadas como `Disponible` para Friend & Family MVP. Todas se apoyan en Tool Layer v2 y datasets `marts.agent_*`; la validación smoke se ejecuta con `backend/scripts/validate_mvp_test_catalog.py`.

## Demografía

| Question | Tool | Status |
|---|---|---|
| ¿Cuál es la sección con mayor población? | `rank_sections` | Disponible |
| ¿Cuál es la sección con menor población? | `rank_sections` | Disponible |
| ¿Qué secciones superan los 5.000 habitantes? | `filter_sections` | Disponible |
| ¿Cuál es la población total de Mijas? | `aggregate_municipality` | Disponible |
| ¿Cómo ha evolucionado la población desde 2021? | `compare_years` | Disponible |
| ¿Qué zonas han crecido más? | `population_growth` | Disponible |

## Edad

| Question | Tool | Status |
|---|---|---|
| ¿Cuál es la sección más joven? | `rank_sections` | Disponible |
| ¿Cuál es la más envejecida? | `rank_sections` | Disponible |
| ¿Dónde viven más menores de 18 años? | `rank_sections` | Disponible |
| ¿Dónde viven más personas mayores de 65 años? | `rank_sections` | Disponible |
| ¿Qué porcentaje de la población tiene menos de 30 años? | `rank_sections` | Disponible |
| ¿Qué secciones tienen más población en edad laboral? | `age_cohort_projection` | Disponible |
| ¿Siempre ha sido la sección más joven? | `compare_years` | Disponible |
| ¿Qué sección ha rejuvenecido más desde 2021? | `compare_years` | Disponible |
| ¿Qué sección ha envejecido más desde 2021? | `compare_years` | Disponible |
| ¿Qué sección ha envejecido más? | `compare_years` | Disponible |
| ¿Qué secciones tienen más menores de 30 años? | `rank_sections` | Disponible |
| ¿Qué secciones tienen más mayores de 65 años? | `rank_sections` | Disponible |
| ¿Qué porcentaje de población joven tiene cada sección? | `rank_sections` | Disponible |
| ¿Qué porcentaje de población jubilada tiene cada sección? | `rank_sections` | Disponible |
| ¿Qué zonas tienen mayor dependencia demográfica? | `cross_metric_ranking` | Disponible |
| ¿Cuántas personas aproximadamente tendrán 18 años en 2027? | `age_cohort_projection` | Disponible |
| ¿Cuántas personas tendrán 18 años en 2027? | `age_cohort_projection` | Disponible |
| ¿Qué secciones tendrán más nuevos votantes en 2027? | `age_cohort_projection` | Disponible |
| ¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027? | `age_cohort_projection` | Disponible |
| ¿Cuántas personas tenían entre 18 y 22 años en 2023? | `age_cohort_projection` | Disponible |
| ¿Cuántas personas entre 18 y 35 años viven en Riviera Sur? | `age_cohort_projection` | Disponible |
| ¿Qué secciones concentran más jóvenes? | `rank_sections` | Disponible |
| ¿Qué secciones concentran más población joven? | `rank_sections` | Disponible |
| ¿Qué secciones concentran más jubilados? | `rank_sections` | Disponible |
| ¿Cuántas personas mayores de 65 años viven en Mijas? | `aggregate_municipality` | Disponible |

## Comportamiento Electoral

| Question | Tool | Status |
|---|---|---|
| ¿Dónde gana el PP siempre? | `persistent_winner` | Disponible |
| ¿Dónde gana siempre el PP? | `persistent_winner` | Disponible |
| ¿Dónde gana el PSOE siempre? | `persistent_winner` | Disponible |
| ¿Dónde gana siempre el PSOE? | `persistent_winner` | Disponible |
| ¿Dónde gana VOX siempre? | `persistent_winner` | Disponible |
| ¿Dónde gana siempre VOX? | `persistent_winner` | Disponible |
| ¿Cuál es el partido históricamente dominante en cada sección? | `historical_party_average` | Disponible |
| ¿Qué partido domina históricamente en Riviera Sur? | `historical_party_average` | Disponible |
| ¿Qué partido es históricamente más fuerte en la sección más joven? | `historical_party_average` | Disponible |
| ¿Qué partido domina la sección más joven? | `historical_party_average` | Disponible |
| ¿Qué partido domina la sección más envejecida? | `historical_party_average` | Disponible |
| ¿Cuál es la sección más favorable al PP? | `party_strength` | Disponible |
| ¿Cuál es la más favorable al PSOE? | `party_strength` | Disponible |
| ¿Cuál es la más favorable a VOX? | `party_strength` | Disponible |
| ¿Cuál es la media histórica de voto del PP? | `historical_party_average` | Disponible |
| ¿Cuál es la media histórica de voto del PSOE? | `historical_party_average` | Disponible |
| ¿Qué sección tiene más abstención? | `rank_sections` | Disponible |
| ¿Cuál tiene menos abstención? | `rank_sections` | Disponible |
| ¿Dónde vota más la gente? | `rank_sections` | Disponible |
| ¿Dónde vota menos la gente? | `rank_sections` | Disponible |
| ¿Qué zonas han reducido más la participación? | `compare_years` | Disponible |
| ¿Cuáles son las secciones más disputadas? | `rank_sections` | Disponible |
| ¿Dónde hay empate técnico entre PP y PSOE? | `rank_sections` | Disponible |
| ¿Dónde tiene más margen de victoria el partido ganador? | `rank_sections` | Disponible |
| ¿En qué sección gana con más diferencia el PSOE? | `party_strength` | Disponible |
| ¿En qué sección gana con más diferencia el PP? | `party_strength` | Disponible |
| ¿Cuáles son las secciones más competitivas? | `rank_sections` | Disponible |
| ¿Qué secciones son más volátiles electoralmente? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones son más conservadoras? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones son más progresistas? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones son más estables? | `rank_sections` | Disponible |
| ¿Qué secciones son más volátiles? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones cambian de partido ganador según la elección? | `historical_party_average` | Disponible |
| ¿Dónde existen patrones electorales persistentes? | `persistent_winner` | Disponible |
| ¿La juventud vota más a la izquierda? | `correlation_analysis` | Disponible |
| ¿La renta alta favorece al PP? | `correlation_analysis` | Disponible |
| ¿Existe relación entre abstención y renta? | `correlation_analysis` | Disponible |
| ¿Existe relación entre edad y participación? | `correlation_analysis` | Disponible |

## Renta

| Question | Tool | Status |
|---|---|---|
| ¿Cuál es la sección más rica? | `rank_sections` | Disponible |
| ¿Cuál es la más pobre? | `rank_sections` | Disponible |
| ¿Qué secciones tienen mayor renta media? | `rank_sections` | Disponible |
| ¿Qué secciones tienen menor renta media? | `rank_sections` | Disponible |
| ¿Qué secciones tienen mayor renta? | `rank_sections` | Disponible |
| ¿Qué secciones tienen menor renta? | `rank_sections` | Disponible |
| ¿Qué zonas combinan renta alta y población joven? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas combinan renta baja y envejecimiento? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas combinan renta baja y abstención elevada? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas muestran mayor desigualdad? | `rank_sections` | Disponible |
| ¿Dónde existe más diferencia entre renta individual y renta del hogar? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas tienen mejor perfil económico? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas muestran señales de vulnerabilidad económica? | `cross_metric_ranking` | Disponible |

## Vivienda

| Question | Tool | Status |
|---|---|---|
| ¿Qué secciones tienen mayor valor inmobiliario? | `rank_sections` | Disponible |
| ¿Qué zonas tienen mayor valor inmobiliario? | `rank_sections` | Disponible |
| ¿Qué secciones tienen menor valor inmobiliario? | `rank_sections` | Disponible |
| ¿Dónde está el mercado más tensionado? | `rank_sections` | Disponible |
| ¿Dónde están las oportunidades inmobiliarias? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas muestran mejor oportunidad inmobiliaria? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones tienen mayor presión residencial? | `rank_sections` | Disponible |
| ¿Qué secciones son consideradas zona prime? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas tienen mayor intensidad edificatoria? | `rank_sections` | Disponible |
| ¿Qué zonas tienen más presión urbanística? | `rank_sections` | Disponible |
| ¿Dónde se concentra más superficie construida? | `rank_sections` | Disponible |
| ¿Qué zonas combinan renta alta y valor inmobiliario alto? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas parecen infravaloradas? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas tienen mayor potencial de revalorización? | `cross_metric_ranking` | Disponible |

## Inteligencia Territorial

| Question | Tool | Status |
|---|---|---|
| ¿Qué secciones tienen más jóvenes y menos renta? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones tienen más mayores y más renta? | `cross_metric_ranking` | Disponible |
| ¿Dónde existe mayor polarización demográfica? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas son más homogéneas? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones presentan más vulnerabilidad social? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas combinan envejecimiento y baja renta? | `cross_metric_ranking` | Disponible |
| ¿Dónde hay más riesgo de exclusión social? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones requieren más servicios públicos? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas parecen más cohesionadas socialmente? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas muestran perfiles más diversos? | `cross_metric_ranking` | Disponible |
| Ordena las secciones por población. | `rank_sections` | Disponible |
| Ordena las secciones por renta. | `rank_sections` | Disponible |
| Ordena las secciones por edad media. | `rank_sections` | Disponible |
| Ordena las secciones por abstención. | `rank_sections` | Disponible |
| ¿Qué zonas concentran más población y crecimiento? | `cross_metric_ranking` | Disponible |
| ¿Qué zonas combinan juventud y crecimiento? | `cross_metric_ranking` | Disponible |
| ¿Qué secciones presentan mejores indicadores territoriales? | `cross_metric_ranking` | Disponible |
