# Ask SocTrace Test Library Validation Report

Generated at: 2026-06-14T17:33:23.751799+00:00

| Categoría | Pregunta | Estado UI | Resultado real | Tool | Motivo | Acción recomendada |
|---|---|---|---|---|---|---|
| Demografia - Poblacion | ¿Cuál es la sección con mayor población? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Poblacion | ¿Cuál es la sección con menor población? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Poblacion | ¿Qué secciones superan los 5.000 habitantes? | Disponible | passed | filter_sections | passed | keep_available |
| Demografia - Poblacion | ¿Cuál es la población total de Mijas? | Disponible | passed | aggregate_municipality | passed | keep_available |
| Demografia - Poblacion | ¿Cómo ha evolucionado la población desde 2021? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Demografia - Poblacion | ¿Qué zonas han crecido más? | Disponible | passed | population_growth | passed | keep_available |
| Demografia - Edad | ¿Cuál es la sección más joven? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Cuál es la más envejecida? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Dónde viven más menores de 18 años? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Dónde viven más personas mayores de 65 años? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Qué porcentaje de la población tiene menos de 30 años? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Demografia - Edad | ¿Qué secciones tienen más población en edad laboral? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Siempre ha sido la sección más joven? | Próximamente | failed | rank_sections | tool mismatch: expected compare_years, got rank_sections | keep_coming_soon |
| Demografia - Edad | ¿Qué sección ha rejuvenecido más desde 2021? | Disponible | passed | compare_years | passed | keep_available |
| Demografia - Edad | ¿Qué sección ha envejecido más desde 2021? | Disponible | passed | compare_years | passed | keep_available |
| Demografia - Edad | ¿Qué sección ha envejecido más? | Disponible | passed | compare_years | passed | keep_available |
| Demografia - Edad | ¿Qué secciones tienen más menores de 30 años? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Qué secciones tienen más mayores de 65 años? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Qué porcentaje de población joven tiene cada sección? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Qué porcentaje de población jubilada tiene cada sección? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Edad | ¿Qué zonas tienen mayor dependencia demográfica? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Demografia - Cohortes | ¿Cuántas personas aproximadamente tendrán 18 años en 2027? | Disponible | passed | age_cohort_projection | passed | keep_available |
| Demografia - Cohortes | ¿Cuántas personas tendrán 18 años en 2027? | Disponible | passed | age_cohort_projection | passed | keep_available |
| Demografia - Cohortes | ¿Qué secciones tendrán más nuevos votantes en 2027? | Disponible | passed | age_cohort_projection | passed | keep_available |
| Demografia - Cohortes | ¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027? | Disponible | passed | age_cohort_projection | passed | keep_available |
| Demografia - Cohortes | ¿Cuántas personas tenían entre 18 y 22 años en 2023? | Próximamente | passed | aggregate_municipality | passed | keep_available |
| Demografia - Cohortes | ¿Cuántas personas entre 18 y 35 años viven en Riviera Sur? | Próximamente | passed | section_age_range | passed | keep_available |
| Demografia - Cohortes | ¿Qué secciones concentran más jóvenes? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Cohortes | ¿Qué secciones concentran más población joven? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Cohortes | ¿Qué secciones concentran más jubilados? | Disponible | passed | rank_sections | passed | keep_available |
| Demografia - Cohortes | ¿Cuántas personas mayores de 65 años viven en Mijas? | Disponible | passed | aggregate_municipality | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana el PP siempre? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana siempre el PP? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana el PSOE siempre? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana siempre el PSOE? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana VOX siempre? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Dónde gana siempre VOX? | Disponible | passed | persistent_winner | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es el partido históricamente dominante en cada sección? | Próximamente | failed | historical_party_average | answer is too thin or not useful | keep_coming_soon |
| Electoral - Partido dominante | ¿Qué partido domina históricamente en Riviera Sur? | Próximamente | failed | historical_party_average | answer is too thin or not useful | keep_coming_soon |
| Electoral - Partido dominante | ¿Qué partido es históricamente más fuerte en la sección más joven? | Próximamente | passed | chained_youngest_section_party_dominance | passed | keep_available |
| Electoral - Partido dominante | ¿Qué partido domina la sección más joven? | Próximamente | passed | chained_youngest_section_party_dominance | passed | keep_available |
| Electoral - Partido dominante | ¿Qué partido domina la sección más envejecida? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es la sección más favorable al PP? | Disponible | passed | party_strength | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es la más favorable al PSOE? | Disponible | passed | party_strength | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es la más favorable a VOX? | Disponible | passed | party_strength | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es la media histórica de voto del PP? | Disponible | passed | historical_party_average | passed | keep_available |
| Electoral - Partido dominante | ¿Cuál es la media histórica de voto del PSOE? | Disponible | passed | historical_party_average | passed | keep_available |
| Electoral - Participacion | ¿Qué sección tiene más abstención? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Participacion | ¿Cuál tiene menos abstención? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Participacion | ¿Dónde vota más la gente? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Participacion | ¿Dónde vota menos la gente? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Participacion | ¿Qué zonas han reducido más la participación? | Próximamente | passed | participation_decline | passed | keep_available |
| Electoral - Evolucion | ¿Qué secciones cambiaron más entre 2019 y 2023? | Disponible | passed | electoral_vote_evolution | passed | keep_available |
| Electoral - Evolucion | ¿Dónde perdió más apoyo el PSOE? | Disponible | passed | electoral_vote_evolution | passed | keep_available |
| Electoral - Evolucion | ¿Dónde ganó más apoyo el PP? | Disponible | passed | electoral_vote_evolution | passed | keep_available |
| Electoral - Evolucion | ¿Dónde creció más VOX? | Disponible | passed | electoral_vote_evolution | passed | keep_available |
| Electoral - Evolucion | ¿Dónde aparecen más partidos locales? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Competitividad | ¿Cuáles son las secciones más disputadas? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Competitividad | ¿Dónde hay empate técnico entre PP y PSOE? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Electoral - Competitividad | ¿Dónde tiene más margen de victoria el partido ganador? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Competitividad | ¿En qué sección gana con más diferencia el PSOE? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Competitividad | ¿En qué sección gana con más diferencia el PP? | Disponible | passed | rank_sections | passed | keep_available |
| Electoral - Competitividad | ¿Cuáles son las secciones más competitivas? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Electoral - Competitividad | ¿Qué secciones son más volátiles electoralmente? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Electoral - Competitividad | ¿Qué secciones son más conservadoras? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Electoral - Competitividad | ¿Qué secciones son más progresistas? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Movilizacion | ¿Dónde debería concentrar esfuerzos el PSOE? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Movilizacion | ¿Dónde debería concentrar esfuerzos el PP? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Movilizacion | ¿Qué secciones tienen más abstencionistas potenciales? | Disponible | passed | mobilizable_abstention_opportunity | passed | keep_available |
| Consultoria politica - Movilizacion | ¿Dónde hay más jóvenes que no votaron? | Disponible | passed | rank_sections | passed | keep_available |
| Consultoria politica - Movilizacion | ¿Qué secciones combinan alta abstención y mucho voto de izquierdas? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Consultoria politica - Movilizacion | ¿Qué secciones combinan alta abstención y mucho voto de derechas? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Consultoria politica - Segmentacion | ¿Dónde vive el votante medio del PP? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Segmentacion | ¿Dónde vive el votante medio del PSOE? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Segmentacion | ¿Qué características tienen las secciones donde gana VOX? | Disponible | passed | rank_sections | passed | keep_available |
| Consultoria politica - Segmentacion | ¿Qué secciones son más sensibles a una campaña de movilización? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Oportunidades | ¿Cuáles son las mejores secciones para ganar un concejal adicional? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Oportunidades | ¿Dónde sería más eficiente invertir 10.000 € en campaña? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Consultoria politica - Oportunidades | ¿Qué secciones presentan más indecisión estructural? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Sociologia - Estructura social | ¿Qué secciones tienen más jóvenes y menos renta? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Sociologia - Estructura social | ¿Qué secciones tienen más mayores y más renta? | Disponible | passed | rank_sections | passed | keep_available |
| Sociologia - Estructura social | ¿Dónde existe mayor polarización demográfica? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Sociologia - Estructura social | ¿Qué zonas son más homogéneas? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Sociologia - Vulnerabilidad | ¿Qué secciones presentan más vulnerabilidad social? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Sociologia - Vulnerabilidad | ¿Qué zonas combinan envejecimiento y baja renta? | Próximamente | failed | compare_years | tool mismatch: expected cross_metric_ranking, got compare_years | keep_coming_soon |
| Sociologia - Vulnerabilidad | ¿Dónde hay más riesgo de exclusión social? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Sociologia - Vulnerabilidad | ¿Qué secciones requieren más servicios públicos? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Sociologia - Cohesion | ¿Qué zonas parecen más cohesionadas socialmente? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Sociologia - Cohesion | ¿Qué zonas muestran perfiles más diversos? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones son más estables? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones son más volátiles? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Ciencia politica - Estabilidad electoral | ¿Qué secciones cambian de partido ganador según la elección? | Próximamente | passed | winner_switch_by_election_type | passed | keep_available |
| Ciencia politica - Estabilidad electoral | ¿Dónde existen patrones electorales persistentes? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Ciencia politica - Comportamiento politico | ¿La juventud vota más a la izquierda? | Disponible | passed | rank_sections | passed | keep_available |
| Ciencia politica - Comportamiento politico | ¿La renta alta favorece al PP? | Disponible | passed | rank_sections | passed | keep_available |
| Ciencia politica - Comportamiento politico | ¿Existe relación entre abstención y renta? | Disponible | passed | correlation_analysis | passed | keep_available |
| Ciencia politica - Comportamiento politico | ¿Existe relación entre edad y participación? | Disponible | passed | correlation_analysis | passed | keep_available |
| Economia - Renta | ¿Cuál es la sección más rica? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Renta | ¿Cuál es la más pobre? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Economia - Renta | ¿Qué secciones tienen mayor renta media? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Renta | ¿Qué secciones tienen menor renta media? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Renta | ¿Qué secciones tienen mayor renta? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Renta | ¿Qué secciones tienen menor renta? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Renta | ¿Qué zonas combinan renta alta y población joven? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Economia - Renta | ¿Qué zonas combinan renta baja y envejecimiento? | Próximamente | failed | compare_years | tool mismatch: expected cross_metric_ranking, got compare_years | keep_coming_soon |
| Economia - Renta | ¿Qué zonas combinan renta baja y abstención elevada? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Economia - Desigualdad | ¿Qué zonas muestran mayor desigualdad? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Economia - Desigualdad | ¿Dónde existe más diferencia entre renta individual y renta del hogar? | Disponible | passed | rank_sections | passed | keep_available |
| Economia - Desarrollo | ¿Qué zonas tienen mejor perfil económico? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Economia - Desarrollo | ¿Qué zonas muestran señales de vulnerabilidad económica? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Inmobiliario - Mercado | ¿Qué secciones tienen mayor valor inmobiliario? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Mercado | ¿Qué zonas tienen mayor valor inmobiliario? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Mercado | ¿Qué secciones tienen menor valor inmobiliario? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Mercado | ¿Dónde está el mercado más tensionado? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Inmobiliario - Mercado | ¿Dónde están las oportunidades inmobiliarias? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Inmobiliario - Mercado | ¿Qué zonas muestran mejor oportunidad inmobiliaria? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Inmobiliario - Mercado | ¿Qué secciones tienen mayor presión residencial? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Mercado | ¿Qué secciones son consideradas zona prime? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Inmobiliario - Construccion | ¿Qué zonas tienen mayor intensidad edificatoria? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Construccion | ¿Qué zonas tienen más presión urbanística? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Construccion | ¿Dónde se concentra más superficie construida? | Disponible | passed | rank_sections | passed | keep_available |
| Inmobiliario - Inversion | ¿Qué zonas combinan renta alta y valor inmobiliario alto? | Próximamente | failed | rank_sections | tool mismatch: expected cross_metric_ranking, got rank_sections | keep_coming_soon |
| Inmobiliario - Inversion | ¿Qué zonas parecen infravaloradas? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Inmobiliario - Inversion | ¿Qué zonas tienen mayor potencial de revalorización? | Disponible | passed | cross_metric_ranking | passed | keep_available |
| Estadistica - Rankings | Ordena las secciones por población. | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Estadistica - Rankings | Ordena las secciones por renta. | Disponible | passed | rank_sections | passed | keep_available |
| Estadistica - Rankings | Ordena las secciones por edad media. | Disponible | passed | rank_sections | passed | keep_available |
| Estadistica - Rankings | Ordena las secciones por abstención. | Disponible | passed | rank_sections | passed | keep_available |
| Estadistica - Desviaciones | ¿Qué secciones están por encima de la media? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Estadistica - Desviaciones | ¿Qué secciones son outliers? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Estadistica - Desviaciones | ¿Qué variable presenta más dispersión? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Estadistica - Distribuciones | ¿Cómo se distribuye la renta? | Disponible | passed | rank_sections | passed | keep_available |
| Estadistica - Distribuciones | ¿Cómo se distribuye la edad? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Estadistica - Distribuciones | ¿Cómo se distribuye la abstención? | Disponible | passed | rank_sections | passed | keep_available |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con la abstención? | Próximamente | failed | rank_sections | tool mismatch: expected correlation_analysis, got rank_sections | keep_coming_soon |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con el voto al PP? | Próximamente | failed | party_strength | tool mismatch: expected correlation_analysis, got party_strength | keep_coming_soon |
| Data Science - Correlaciones | ¿Qué variables se relacionan más con el voto al PSOE? | Próximamente | failed | party_strength | tool mismatch: expected correlation_analysis, got party_strength | keep_coming_soon |
| Data Science - Clustering | Agrupa secciones similares. | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Clustering | ¿Qué secciones se parecen a Riviera Sur? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Clustering | ¿Qué secciones tienen perfiles equivalentes? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Scores | Crea un índice de vulnerabilidad. | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Scores | Crea un índice de oportunidad electoral. | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Scores | Crea un índice de presión inmobiliaria. | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Scores | ¿Qué zonas concentran más población y crecimiento? | Disponible | passed | population_growth | passed | keep_available |
| Data Science - Scores | ¿Qué zonas combinan juventud y crecimiento? | Disponible | passed | population_growth | passed | keep_available |
| Data Science - Scores | ¿Qué secciones presentan mejores indicadores territoriales? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Data Science - Prediccion | ¿Qué secciones podrían aumentar la abstención? | Próximamente | passed | abstention_increase_risk | passed | keep_available |
| Data Science - Prediccion | ¿Qué secciones podrían cambiar de ganador? | Próximamente | failed | population_growth | no supported executable tool for this forecast-style question | keep_coming_soon |
| Data Science - Prediccion | ¿Qué secciones podrían crecer más demográficamente? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Conversacional - Contexto 1 | ¿Cuál es la sección más joven? | Disponible | passed | rank_sections | passed | keep_available |
| Conversacional - Contexto 1 | ¿Siempre ha sido la más joven? | Próximamente | failed | rank_sections | tool mismatch: expected compare_years, got rank_sections | keep_coming_soon |
| Conversacional - Contexto 1 | ¿Qué partido es históricamente más fuerte allí? | Próximamente | failed | historical_party_average | answer is too thin or not useful | keep_coming_soon |
| Conversacional - Contexto 1 | ¿Y qué renta tiene? | Próximamente | failed | rank_sections | tool mismatch: expected section_profile, got rank_sections | keep_coming_soon |
| Conversacional - Contexto 1 | ¿Está por encima o por debajo de la media de Mijas? | Próximamente | failed |  | no tool selected | keep_coming_soon |
| Conversacional - Contexto 2 | ¿Dónde gana siempre el PP? | Disponible | passed | persistent_winner | passed | keep_available |
| Conversacional - Contexto 2 | ¿Cuál de esas secciones tiene más población? | Disponible | passed | rank_sections | passed | keep_available |
| Conversacional - Contexto 2 | ¿Y cuál es la más joven? | Disponible | passed | rank_sections | passed | keep_available |
| Conversacional - Contexto 2 | ¿Qué partido queda segundo en ella? | Próximamente | failed |  | no tool selected | keep_coming_soon |
