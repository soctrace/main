# Inventario técnico y funcional de Ask SocTrace / Municipal Intelligence Agent

Fecha de auditoría: 2026-06-08  
Alcance: Fase 0, auditoría sin cambios funcionales.  
Base de datos viva: comprobación parcial realizada sobre `psql -d mijas` para objetos clave. Cuando no se ha comprobado en base viva se indica `No verificado`.

## 1. Estructura relevante del proyecto

| Área | Ruta | Observaciones |
|---|---|---|
| Frontend principal | `soctrace-web/src` | Aplicación React/Vite con dashboard, mapa, sidebars y Ask SocTrace. |
| Ask SocTrace frontend | `soctrace-web/src/features/ask-soctrace` | Componentes, hook, servicio API, tipos y biblioteca de tests preconfigurados. |
| Panel Ask SocTrace | `soctrace-web/src/features/ask-soctrace/components/AskSocTracePanel.tsx` | Renderiza respuestas, entidades, CTAs, tabla en modo detallado/debug y estado de carga. |
| Servicio Ask frontend | `soctrace-web/src/features/ask-soctrace/services/askSocTraceService.ts` | Adapta respuesta backend a contrato UI; construye tabla/chart fallback. |
| Hook conversación frontend | `soctrace-web/src/features/ask-soctrace/hooks/useAskSocTrace.ts` | Guarda `conversationId` en `localStorage`; mensajes en memoria React. |
| Biblioteca de tests UI | `soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts` | 29 categorías, 109 prompts. Muchos son aspiracionales. |
| Dashboard frontend | `soctrace-web/src/components/layout`, `soctrace-web/src/store` | RightSidebar contiene test library y paneles de capas; store centraliza filtros y estado. |
| Backend FastAPI | `backend/app` | API, servicios, repositorios, schemas y Ask SocTrace. |
| Ask SocTrace backend | `backend/app/ask` | Servicio principal, catálogo semántico, SQL generator, tools, planner, memoria y orquestación. |
| Catálogo semántico | `backend/app/ask/semantic_catalog.yaml` | Define vistas aprobadas, métricas, operaciones y joins. Mezcla versión nueva `metrics` con bloque legado `approved_metrics`. |
| Intérprete semántico | `backend/app/ask/semantic_layer.py` | Mapea preguntas a `AnalyticalOperation`; usa reglas deterministas sobre el catálogo. |
| Generador SQL | `backend/app/ask/sql/sql_generator.py` | Contiene numerosos builders deterministas y planes semánticos. |
| Validador SQL | `backend/app/ask/sql/sql_validator.py` | Bloquea DDL/DML y limita relaciones a catálogo aprobado. |
| Ejecutor SQL | `backend/app/ask/sql/query_executor.py` | Ejecuta SQLAlchemy text con `statement_timeout` y `LIMIT` externo si falta. |
| Tool registry | `backend/app/ask/tools/registry.py` | Define herramientas OpenAI/function-calling y handlers sobre `AnalystRepository`. |
| Memoria conversacional | `backend/app/ask/conversation` | Store en memoria de proceso, follow-up resolver y estructuras Pydantic. |
| Rutas API Ask | `backend/app/api/v1/routes/ask.py` | Expone `/ask` y `/agent/chat`, ambos llaman a `AskSocTraceService.ask`. |
| Ruta Local Analyst legada | `backend/app/api/v1/routes/analyst.py` | Expone `/analyst/ask` usando `LocalAnalystService`; convive con Ask SocTrace. |
| SQL/migraciones | `sql/raw`, `sql/staging`, `sql/core`, `sql/marts`, `sql/qa` | No hay sistema de migración formal detectado; son scripts numerados. |
| ETL | `etl` | Carga demografía, renta, electoral, geografía, catastro y vivienda. |
| Tests backend | `backend/tests`, `backend/tests/ask` | Tests unitarios/semánticos y algunos con DB local. |
| Streamlit legado | `app` | App Streamlit anterior, componentes y páginas. |
| Packs municipales | `municipality_packs/mijas` | Contexto, metodología, historia electoral y metadata de Mijas. |

## 2. Inventario de tablas y vistas usadas por el agente

Comprobación de base viva para objetos clave: `core.poblacion_edad`, `marts.ask_population_profile`, `marts.ask_section_profile`, `marts.housing_intelligence_features_2023`, `marts.mijas_features_panel`, `marts.mv_electoral_behavior`, `marts.v_income_level_layer`, `marts.v_land_built_environment`, `marts.v_mapa_age_structure_2023`, `marts.v_population_layer` existen. No aparecieron en la comprobación: `marts.ask_population_age`, `marts.ask_population_age_range`, `marts.ask_electoral_results`, `marts.ask_electoral_summary`, `marts.ask_income`, `marts.ask_housing`, `marts.ask_section_lookup`.

| Nombre | Existe en SQL | Confirmado en DB viva | Usada por | Estado | Comentarios |
|---|---:|---:|---|---|---|
| `core.poblacion_edad` | Sí | Sí | cohortes, edad, tools, SQL generator | OK | Tabla base por sección, año, género y cohorte. |
| `marts.ask_population_profile` | Sí, `sql/marts/027_ask_population_profile.sql` | Sí | métricas población/edad, growth | OK parcial | Vista ask estable para población; usada correctamente en tests de población. |
| `marts.ask_section_profile` | Sí, dos definiciones: `026` y `027` | Sí | renta, electoral y perfil de sección en catálogo | Parcial/Riesgo | En DB viva tiene 181 filas, pero `income_individual`, `abstention_pct`, `winner_party` tienen 0 no nulos. La definición `027` pisa con `NULL` campos socioeconómicos/electorales. |
| `marts.ask_population_age` | Sí, `026` | No | catálogo `approved_views`; antes usada para cohortes | Rota en DB viva | Definida en SQL pero no aplicada en DB comprobada. |
| `marts.ask_population_age_range` | Sí, `026` | No | catálogo | Rota en DB viva | Fuente semántica declarada, no disponible en DB viva comprobada. |
| `marts.ask_electoral_results` | Sí, `026` | No | `vote_pct`, party strength | Rota en DB viva | Métrica `vote_pct` puede fallar si usa vista ask. |
| `marts.ask_electoral_summary` | Sí, `026` | No | abstención, participación, winner | Rota en DB viva | Métricas electorales semánticas apuntan aquí. |
| `marts.ask_income` | Sí, `026` | No | catálogo | Rota en DB viva | Alternativa real usada por handlers: `marts.v_income_level_layer`. |
| `marts.ask_housing` | Sí, `026` | No | métricas inmobiliarias del catálogo | Rota en DB viva | Depende de `marts.housing_intelligence_features_2023`, que sí existe. |
| `marts.ask_section_lookup` | Sí, `026` | No | vistas ask de `026` | Rota en DB viva | Su ausencia rompe vistas `ask_` de `026` si se esperan en runtime. |
| `marts.v_mapa_age_structure_2023` | Sí | Sí | edad media, juventud, repositorio analyst | OK | También existe `marts.v_mapa_age_structure` para histórico. |
| `marts.v_mapa_age_structure` | Sí | No verificado | histórico edad media | Probable OK | Usada por consistencia histórica de sección joven. |
| `marts.v_population_layer` | Sí | Sí | `ask_population_profile`, dashboard, repositorio | OK | Capa población por año/sección. |
| `marts.v_poblacion_seccion_anio` | Sí | No verificado | catálogo legado, direct handlers | OK probable | Vista agregada de población; usada por handlers antiguos. |
| `marts.v_income_level_layer` | Sí | Sí | renta en handlers y repositorio | OK | Fuente operativa para renta. |
| `marts.mv_electoral_behavior` | Sí | Sí | electoral, tools, Ask | OK | Fuente electoral central con JSON de partidos. |
| `marts.v_resultados_seccion_eleccion` | Sí | No verificado | `ask_electoral_results` | OK probable | Normaliza resultados electorales por partido. |
| `marts.dim_seccion_display` | Sí, duplicada en `005` y `006` | No verificado en consulta clave, usada | Duplicada | Dos scripts crean la misma tabla; riesgo de orden de ejecución. |
| `marts.mijas_features_panel` | Sí | Sí | QA, territorial intelligence | OK/Prototipo | Materialized view Mijas-specific; no generalizable multi-municipio. |
| `marts.v_land_built_environment` | Sí | Sí | inmobiliario/territorio | OK | Usada por repositorio y dashboard. |
| `marts.housing_intelligence_features_2023` | Sí | Sí | vivienda/calidad de vida, `ask_housing` | OK | Capa 2023 específica. |
| `core.resultados_seccion` | Sí | No verificado | LocalAnalyst/tools | OK probable | Fuente electoral histórica core. |
| `core.agent_audit_log` | Sí | No verificado | forecast/analyst repository | OK probable | Tabla de auditoría; no se detecta uso directo por Ask SocTrace v1. |

### Observaciones SQL/migraciones

| Hallazgo | Impacto | Recomendación |
|---|---|---|
| No hay migrador formal detectado; scripts SQL numerados dependen del orden manual. | Alto | Crear migración reproducible y una vista `agent_*` estable. |
| `sql/marts/026_ask_analytical_views.sql` y `027_ask_population_profile.sql` definen `marts.ask_section_profile` con lógicas distintas. | Alto | Unificar `ask_section_profile`; evitar que `027` sobrescriba campos con `NULL`. |
| Varias vistas `ask_` declaradas en catálogo no existen en DB viva comprobada. | Alto | Aplicar/recrear `026` o cambiar catálogo a fuentes existentes. |
| `marts.mijas_features_panel` y varias vistas forecast son Mijas-specific. | Medio | Separar objetos multi-municipio de objetos Mijas-only. |
| `DROP VIEW` aparece en algunos scripts de marts. | Medio | Controlar orden y dependencias; mover a migración idempotente. |

## 3. Métricas semánticas detectadas

Fuente principal: `backend/app/ask/semantic_catalog.yaml`, bloque `metrics`.

| Métrica | Sinónimos principales | Vista/campo | Operaciones | Estado |
|---|---|---|---|---|
| `population_total` | población total, mayor población, más habitantes | `marts.ask_population_profile.population_total` | `rank_sections` | OK |
| `population_density` | densidad de población, mayor densidad | `marts.ask_population_profile.population_density` | `rank_sections` | OK |
| `population_growth_abs` | zonas han crecido más, ganado habitantes | `marts.ask_population_profile.population_total` | `rank_population_growth_zones` | OK parcial; requiere lineage. |
| `population_growth_over_time` | crecimiento demográfico | `marts.ask_population_profile.population_total` | `rank_population_growth_zones` | OK parcial; duplicada con `population_growth_abs`. |
| `population_growth_pct` | crecimiento porcentual, relativo | `marts.ask_population_profile.population_total` | `rank_section_growth` en catálogo; builder real usa `rank_population_growth_zones` | Inconsistente |
| `average_age` | edad media, sección más joven, más envejecida | `marts.ask_population_profile.average_age` | `rank_sections` | OK para último año; histórico usa otra vista. |
| `population_under_30` | jóvenes, menores de 30 | `marts.ask_population_profile.population_under_30` | `rank_sections` | OK, pero demasiado genérica y compite con cohortes específicas. |
| `population_under_30_pct` | porcentaje jóvenes, peso joven | `marts.ask_population_profile.population_under_30_pct` | `rank_sections` | OK parcial; riesgo de responder sección cuando se pregunta total municipal. |
| `population_over_65` | mayores de 65, población mayor | `marts.ask_population_profile.population_over_65` | `rank_sections` | OK |
| `population_over_65_pct` | porcentaje mayores, senior share | `marts.ask_population_profile.population_over_65_pct` | `rank_sections` | OK parcial; mismo riesgo municipal vs sección. |
| `income_individual` | renta individual, sección rica/pobre | `marts.ask_section_profile.income_individual` | `rank_sections` | Rota en DB viva: campo todo `NULL`. |
| `income_household` | renta hogar, renta familiar | `marts.ask_section_profile.income_household` | `rank_sections` | Rota en DB viva: probable `NULL`. |
| `abstention_pct` | abstención, no votaron | `marts.ask_electoral_summary.abstention_pct` | `rank_sections` | Rota si usa vista ask; vista no existe en DB viva. |
| `participation_pct` | participación, votaron más | `marts.ask_electoral_summary.participation_pct` | `rank_sections` | Rota si usa vista ask; vista no existe en DB viva. |
| `vote_pct` | voto al PP/PSOE/VOX, más fuerte | `marts.ask_electoral_results.vote_pct` | `get_party_strength`, `rank_sections` | Rota si usa vista ask; herramientas usan `mv_electoral_behavior`. |
| `winner_party` | ganador, primera fuerza, gana siempre | `marts.ask_electoral_summary.winner_party` | `get_persistent_winners`, `rank_sections` | Rota si usa vista ask; handler alternativo usa `mv_electoral_behavior`. |
| `estimated_real_estate_value_m2` | valor inmobiliario, precio m2 | `marts.ask_housing.estimated_real_estate_value_m2` | `rank_sections` | Rota en DB viva: `ask_housing` no existe. |
| `residential_pressure_index` | presión residencial | `marts.ask_housing.residential_pressure_index` | `rank_sections` | Rota en DB viva. |
| `urban_intensity_index` | intensidad construida/urbana | `marts.ask_housing.urban_intensity_index` | `rank_sections` | Rota en DB viva. |

### Problemas del catálogo

| Problema | Ejemplo | Impacto |
|---|---|---|
| Doble sistema de métricas | `metrics` y `approved_metrics` en el mismo YAML | Dificulta saber qué bloque manda. |
| Vistas declaradas pero ausentes en DB viva | `marts.ask_electoral_summary`, `marts.ask_housing` | Preguntas pueden fallar aunque el catálogo diga OK. |
| Métricas apuntan a campos nulos | `income_individual` en `ask_section_profile` | Respuestas vacías o fallos. |
| Operaciones declaradas sin builder explícito | `get_metric_by_section`, `compare_metrics_by_section`, `aggregate_population`, `calculate_derived_indicator` | Catálogo promete más de lo implementado. |
| Sinónimos demasiado amplios | `jóvenes`, `más joven`, `mayores` | Rutas erróneas entre edad media, menores de 30 y cohortes concretas. |
| Campos frontend/backend inconsistentes | `sectionName` vs `section_name`, `chartSpec` vs `chart_spec` | Adaptadores manuales y riesgo de pérdida de información. |

## 4. Operaciones analíticas existentes

| Operación | Archivo | Input esperado | Output | Clasificación | Estado | Comentarios |
|---|---|---|---|---|---|---|
| `rank_sections` | `semantic_layer.py`, `sql_generator.py` | métrica, orden, año, municipio | ranking/single | Reusable | Parcial | Funciona si la vista/campo existe; depende del catálogo. |
| `get_party_strength` | `semantic_layer.py`, `sql_generator.py` | partido, elección, año | ranking | Reusable | Parcial | Builder semántico usa `marts.ask_electoral_results`, no existe en DB viva. |
| `get_persistent_winners` | `semantic_layer.py`, `sql_generator.py` | partido, elección | ranking | Reusable | Parcial | Builder semántico usa `marts.ask_electoral_summary`; handler alternativo usa `mv_electoral_behavior`. |
| `rank_population_growth_zones` | `semantic_layer.py`, `sql_generator.py` | start/end year, lineage, rank_by | ranking | Reusable | OK parcial | Usa `section_lineage.yaml`; responde división histórica. |
| `future_age_cohort_projection` | `semantic_layer.py`, `sql_generator.py` | sourceYear/sourceAge/targetYear/targetAge | tabla/ranking | One-off reusable | OK reciente | Estima futuros 18 años en 2027 desde cohorte 15-19 de 2025. |
| `municipality_population_total` | `sql_generator.py` | municipio | single value | Reusable | OK | Agrega `ask_population_profile`. |
| `municipality_population_trend` | `sql_generator.py` | start year, municipio | chart line | Reusable | OK | Serie municipal desde `ask_population_profile`. |
| `population_threshold_sections` | `sql_generator.py` | umbral población | entity_list | Reusable | OK | Ej. secciones > 5.000 habitantes. |
| `age_cohort_turnout_estimation` | `sql_generator.py` | rango edad + elección | ranking | Reusable | Parcial | Estimación ecológica por sección; SQL directo sobre `core.poblacion_edad` y `mv_electoral_behavior`. |
| `party_always_wins_by_section` | `sql_generator.py`, `service.py` | partido | ranking | Reusable | Parcial | Dos caminos: semantic SQL y agent loop. |
| `young_population_high_abstention_sections` | `sql_generator.py` | año | ranking score | One-off | Parcial | Score compuesto, no medida directa. |
| `historical_party_average_by_section` | `sql_generator.py`, tools | partido | ranking | Reusable | Parcial | Usa medias históricas; depende de normalización electoral. |
| `high_income_high_party_vote_sections` | `sql_generator.py` | partido, año | scatter/ranking | One-off | Parcial | Combina percent_rank de renta y voto. |
| `previous_sections_winner_count` | `planner.py`, `sql_generator.py`, tools | secciones previas, partido/año | tabla/conteo | Reusable conversacional | Parcial | Depende de memoria de secciones. |
| `historical_extreme_consistency` | `service.py` agent loop | sección previa, métrica edad | yes/no | One-off | Parcial | Falla si no hay contexto; antes asumía sección. |
| `historical_party_dominance_for_section` | `service.py` agent loop | sección previa o sección más joven | tabla histórica | One-off | Parcial | Útil pero acoplado a “sección más joven”. |
| `demographics_age_range` | `tools/registry.py` | minAge, maxAge, year, groupBy | total/rows | Reusable tool | OK parcial | Tool OpenAI/fallback; rangos cortados se prorratean. |
| `age_cohort_abstention_by_section` | `tools/registry.py` | rango edad, elección, año | rows/totals | Reusable tool | OK parcial | Preferida para edad + voto/abstención. |
| `elections_party_section_history` | `tools/registry.py` | sección, partido | histórico | Reusable tool | OK parcial | Resuelve sección por nombre/código. |
| `elections_party_historical_average` | `tools/registry.py` | partido | topSections | Reusable tool | OK parcial | Media histórica por sección. |
| `elections_ranking` | `tools/registry.py` | partido, año | ranking | Reusable tool | OK parcial | Usa repositorio local. |
| `winner_party_by_section_set` | `tools/registry.py` | sectionIds, elección, año | rows | Reusable tool | OK parcial | Para follow-ups “esas secciones”. |
| `socioeconomic_similarity` | `tools/registry.py` | sectionIds, indicadores | perfil | Reusable tool | Parcial | No siempre se sintetiza con detalle. |
| `socioeconomic_section_profile` | `tools/registry.py` | sectionIds | perfil | Reusable tool | Parcial | Follow-ups de renta/edad. |
| `dhondt_calculator` | `tools/registry.py` | año, seats, threshold | seats/quotients | Reusable tool | OK | Calcula D'Hondt desde votos observados. |
| `available_datasets` | `tools/registry.py` | municipio | disponibilidad | Reusable tool | OK parcial | Orienta preguntas no mapeadas. |
| `get_metric_by_section` | `semantic_catalog.yaml` | métrica/sección | No encontrado | Declarada | No implementada claramente | Operación prometida por catálogo. |
| `compare_metrics_by_section` | `semantic_catalog.yaml` | métricas/secciones | No encontrado | Declarada | No implementada claramente | Falta builder universal. |
| `aggregate_population` | `semantic_catalog.yaml` | población/filtros | No encontrado | Declarada | No implementada como operación genérica | Existen handlers específicos. |
| `calculate_derived_indicator` | `semantic_catalog.yaml` | score | No encontrado | Declarada | No implementada como genérica | Tests Data Science son aspiracionales. |

## 5. Estado de integración LLM

| Elemento | Estado | Observaciones |
|---|---|---|
| `OPENAI_API_KEY` | Configurado como env en `Settings.openai_api_key` | No se encontró clave hardcodeada en archivos inspeccionados. |
| Modelo | `gpt-4.1-mini` por defecto | Definido en `backend/app/core/config.py`. |
| Timeout | Sí | `openai_timeout_seconds = 20.0`. |
| Backend llama LLM | Sí, condicional | `QuestionInterpreter` para interpretación y `AskSocTraceService._ask_with_openai` para Responses API. |
| Frontend llama LLM | No encontrado | Frontend llama API local `askSocTraceAgent`. |
| Tool calling | Sí/parcial | `ToolRegistry.openai_tools()` se pasa a `client.responses.create`. |
| LLM como planner | Parcial | Hay prompt `PLANNER_PROMPT`, pero `SocTracePlanner` actual es determinista; LLM interpreta intención si hay API key. |
| Fallback sin LLM | Sí | `AskSocTraceService._ask_with_fallback` y muchos SQL builders deterministas. |
| Guardrails coste | Parcial | `ask_max_tool_calls = 4`, `max_output_tokens=1200`, timeout. No hay tracking coste/token. |
| Riesgo de API key frontend | Bajo | No encontrado uso directo de OpenAI en React. |
| Riesgo de prompt/tool drift | Medio | El LLM puede elegir tools, pero muchas respuestas ya se resuelven antes por rutas deterministas. |

## 6. Auditoría de ejecución SQL

| Elemento | Estado | Riesgo | Recomendación |
|---|---|---|---|
| SQL libre generado por LLM | No directo en ruta principal | Medio | Mantener el LLM sin capacidad de SQL libre; que elija tools/operaciones. |
| SQL generado por código determinista | Sí | Medio | Consolidar builders en tool layer universal. |
| Validador de relaciones aprobadas | Sí | Medio | Funciona para `FROM/JOIN schema.table`; no valida columnas ni CTE shadowing complejo. |
| Bloqueo DDL/DML | Sí | Bajo | Regex bloquea insert/update/drop/create/etc. |
| Solo SELECT/WITH | Sí | Bajo | Validador exige `select` o `with`. |
| Comentarios SQL bloqueados | Sí | Bajo | Bloquea `--` y `/*`. |
| Acceso a catálogos sistema | Bloqueado | Bajo | Bloquea `pg_catalog` e `information_schema`. |
| Queries parametrizadas | No | Medio | Se usan f-strings; entradas suelen normalizadas pero conviene parametrizar o whitelist estricta. |
| LIMIT | Sí | Bajo | `QueryExecutor` añade límite 100 si no detecta `LIMIT`. |
| Timeout | Sí | Bajo | `SET LOCAL statement_timeout = 5000`. |
| Usuario read-only | No verificado | Medio | No se confirma que `database_url` use rol read-only. |
| Catálogo aprobado vs DB real | Inconsistente | Alto | Varias vistas aprobadas no existen en DB viva; rompe seguridad funcional. |

## 7. Memoria conversacional

| Elemento | Estado | Comentarios |
|---|---|---|
| `conversationId` frontend | Sí | Se crea en `useAskSocTrace` y se guarda en `localStorage` bajo `soctrace.ask.session_id`. |
| Mensajes frontend | En memoria React | No sobreviven a reload aunque `conversationId` sí. |
| Store backend | En memoria de proceso | `ConversationStore._states`; no persiste en DB. |
| Supervivencia a restart backend | No | Se pierde toda memoria conversacional. |
| `lastAnswerContext` | Sí | Guarda pregunta, resumen, operación, métrica, años, secciones, tabla, chartSpec, metodología y cautelas. |
| `lastSections` / `lastSection` | Sí | Se usa para follow-ups tipo “esas secciones”. |
| `lastMetric` / `lastYear` / `lastAgeRange` | Sí | Usados por referencia y follow-up resolver. |
| `FollowUpResolver` | Sí | Resuelve año usado, metodología, tabla, conteo, cambio de año, porcentaje y secciones previas. |
| CTAs sugeridas mantienen conversación | Sí | `askSuggestedQuestion` usa el mismo hook y `conversationId`. |
| Riesgo | Medio | Memoria global de proceso sin TTL ni aislamiento persistente; si hay varios usuarios con mismo localStorage viejo, podría mezclar contexto en despliegues simples. |

## 8. Renderizado de respuestas

| Componente | Estado | Problemas detectados |
|---|---|---|
| `AskResponse` backend | Flexible | Campos camelCase (`chartSpec`, `suggestedFollowUps`) y alias frontend (`chart_spec`) se adaptan manualmente. |
| Modo simple | Sí | Solo muestra answer, entidades, caveat corto y CTAs; tablas ocultas salvo modo detallado/debug. |
| Modo detallado/debug | Sí | Backend puede ocultar debug si no se pide; frontend muestra tabla/metodología/cautelas/debug. |
| `chartSpec` | Parcial | Backend devuelve `chartSpec`; frontend lo adapta a `chart_spec` y manda a zona de gráficos. No hay contrato tipado fuerte. |
| Suggested CTAs | Sí | Se validan en backend; frontend renderiza botones. Aún pueden existir CTAs aspiracionales desde tests/config. |
| Technical field leakage | Parcial | Tablas usan columnas crudas (`section_id`, `municipio_nombre`, `estimated_future_age_population`); en UI detallada pueden aparecer nombres técnicos. |
| Simple answer renderer | Funciona | No hay efecto typewriter/streaming detectado; la respuesta aparece de golpe. |
| Chart renderer | Parcial | Gráficos dependen de `setAskChartResponse` y de que `chart_spec.kind !== "none"`. |
| Métricas/cards irrelevantes | Parcial | Adaptador frontend crea métricas solo para abstención por cohorte; otros totals no se traducen a cards. |
| Error frontend | Parcial | Mensaje de error está en inglés: “The local analytical service...”. |

## 9. Tests preconfigurados actuales

Archivo: `soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts`.

| Categoría | Número de tests | Estado |
|---|---:|---|
| Demografia - Poblacion | 5 | Bastante cubierta por tests backend. |
| Demografia - Edad | 9 | Parcial; varios casos aún no tienen operación robusta. |
| Demografia - Cohortes | 7 | Parcial; primer voto 2027 cubierto, jubilados y 18-22 requieren más soporte. |
| Electoral - Partido dominante | 8 | Parcial; depende de rutas electorales y vistas ask ausentes. |
| Electoral - Participacion | 5 | Parcial; algunas rutas existen, evolución participación no clara. |
| Electoral - Evolucion | 5 | Probablemente aspiracional. |
| Electoral - Competitividad | 3 | Probablemente aspiracional. |
| Consultoria politica - Movilizacion | 6 | Parcial/aspiracional. |
| Consultoria politica - Segmentacion | 4 | Aspiracional. |
| Consultoria politica - Oportunidades | 3 | Aspiracional salvo D'Hondt relacionado. |
| Sociologia - Estructura social | 4 | Aspiracional. |
| Sociologia - Vulnerabilidad | 4 | Aspiracional. |
| Sociologia - Cohesion | 2 | Aspiracional. |
| Ciencia politica - Estabilidad electoral | 4 | Parcial. |
| Ciencia politica - Comportamiento politico | 4 | Aspiracional/correlaciones no robustas. |
| Economia - Renta | 4 | Rota si usa `ask_section_profile`; handlers alternos pueden funcionar. |
| Economia - Desigualdad | 2 | Aspiracional. |
| Economia - Desarrollo | 2 | Aspiracional. |
| Inmobiliario - Mercado | 4 | Rota si usa `ask_housing`, ausente en DB viva. |
| Inmobiliario - Construccion | 3 | Parcial con `v_land_built_environment`, no con `ask_housing`. |
| Inmobiliario - Inversion | 3 | Aspiracional. |
| Estadistica - Rankings | 4 | Parcial para población/edad; renta/abstención frágiles. |
| Estadistica - Desviaciones | 3 | Aspiracional. |
| Estadistica - Distribuciones | 3 | Aspiracional. |
| Data Science - Correlaciones | 3 | Aspiracional. |
| Data Science - Clustering | 3 | Aspiracional. |
| Data Science - Scores | 3 | Aspiracional. |
| Data Science - Prediccion | 3 | Aspiracional. |
| Conversacional - Contexto 1 | 5 | Parcial; depende de memoria y sección previa. |
| Conversacional - Contexto 2 | 4 | Parcial. |

### Tests backend existentes

| Archivo | Cobertura principal |
|---|---|
| `backend/tests/ask/test_semantic_layer.py` | Mapeo semántico, SQL validado, growth, primer voto 2027, multi-municipio básico. |
| `backend/tests/ask/test_population_semantic.py` | Ejecución con DB para población, growth, primer voto 2027, CTAs ejecutables de población. |
| `backend/tests/ask/test_followup_memory.py` | Follow-ups sobre año, periodo, metodología, conteo y cambio de año. |
| `backend/tests/test_local_analyst.py` | Router legacy, D'Hondt, golden tests de conversación, composite age+abstention. |

### Prompts probablemente rotos o no soportados

| Prompt | Motivo probable |
|---|---|
| `¿Qué secciones concentran más jubilados?` | No hay operación que combine 65+ con `Pensión`/fuentes de ingresos. |
| `¿Qué sección ha rejuvenecido más desde 2021?` | No hay operación implementada para cambio temporal de porcentaje joven por sección. |
| `¿Qué sección ha envejecido más desde 2021?` | Igual, pero para 65+. |
| `¿Qué secciones tienen más población en edad laboral?` | No hay métrica `working_age_pct` configurada. |
| `¿Dónde existe mayor polarización demográfica?` | No hay definición semántica ni score. |
| `¿Cuáles son las secciones más disputadas?` | No encontrado builder de competitividad/margen. |
| `¿Existe relación entre abstención y renta?` | No hay operación de correlación universal. |
| `Agrupa secciones similares.` | No hay clustering runtime. |
| `Crea un índice de vulnerabilidad.` | No hay tool de score configurable. |
| `¿Qué zonas tienen mayor valor inmobiliario?` | Catálogo apunta a `marts.ask_housing`, ausente en DB viva. |

## 10. Known failure cases

| Pregunta | Resultado actual observado/esperado | Causa probable | Solución recomendada |
|---|---|---|---|
| `¿Qué secciones concentran más jubilados?` | Antes no encontraba operación; debería combinar mayores de 65 y variable `Pensión`. | Falta métrica/operación para jubilados; `Pensión` vive en subcapa Potencial Productivo/fuentes de ingresos, no en catálogo Ask. | Crear vista `agent_income_sources_by_section` y operación `retirement_concentration`. |
| `¿Qué sección ha rejuvenecido más desde 2021?` | No encuentra operación. | No existe builder para comparar `population_under_30_pct` entre años por sección/lineage. | Crear operación `rank_age_share_change` con cohortes y años. |
| `¿Son datos de 2025?` | Follow-up ahora puede responder si `lastAnswerContext.year` está poblado; antes era inconsistente. | Memoria dependiente de que la respuesta previa haya registrado año/periodo. | Estandarizar metadata temporal en todos los renderers. |
| `¿Qué zonas han crecido más?` | Actualmente cubierta y testeada; antes podía mezclar secciones tras split. | Necesidad de lineage manual para secciones divididas. | Mantener `section_lineage.yaml`, pero convertirlo en tabla/vista versionada. |
| `¿Cuántas personas aproximadamente tendrán 18 en 2027?` | Corregida recientemente; antes respondía menores de 30. | Sin guard de routing; sin operación de proyección de cohorte. | Mantener operación `future_age_cohort_projection`; migrar a vista agent estable de cohortes. |
| `¿Cuál es la sección con mayor población?` | Actualmente cubierta y testeada. | Riesgo si agent loop intercepta o si `ask_population_profile` no existe. | Mantener test de ejecución y contrato `agent_population_profile`. |

## 11. Agent Readiness Score

| Categoría | Puntuación 0-5 | Justificación |
|---|---:|---|
| Datos | 3 | Hay datos ricos en core/marts, pero varias vistas `ask_` declaradas no existen en DB viva y hay objetos Mijas-specific. |
| Capa semántica | 2 | Catálogo útil pero inconsistente: doble bloque, vistas ausentes, sinónimos amplios y operaciones prometidas sin builder. |
| Operaciones analíticas | 2 | Muchas rutas útiles, pero mezcladas entre one-off handlers, SQL generator, tools y agent loop. |
| SQL seguro | 3 | Buen validador básico, timeout y limit; falta parametrización y rol read-only verificado. |
| LLM/tool calling | 2 | Integración Responses API existe, pero no es el planner central; depende de fallback/determinismo y catálogo incoherente. |
| Memoria conversacional | 2 | Funciona en memoria local y CTAs mantienen sesión, pero no persiste ni tiene modelo robusto multiusuario. |
| Renderizado | 2 | Respuestas simples funcionan; tablas/campos técnicos y chartSpec tienen contrato débil; sin streaming/typewriter. |
| Tests | 2 | Hay tests valiosos para población/semántica/follow-up, pero la biblioteca UI de tests es mayoritariamente aspiracional. |
| Escalabilidad multi-municipio | 1 | `municipality_id` existe, pero muchas vistas, nombres y escenarios están acoplados a Mijas. |

Puntuación media aproximada: 2,2 / 5. Estado: prototipo avanzado, no listo todavía como Municipal Intelligence Agent v1.

## 12. Recommended next steps

### Fase 1 — Crear vistas `agent_` estables

| Elemento | Detalle |
|---|---|
| Archivos | Crear `sql/marts/030_agent_core_views.sql` o equivalente migración formal. |
| Entregables | `marts.agent_section_profile`, `marts.agent_population_age`, `marts.agent_electoral_results`, `marts.agent_income_sources`, `marts.agent_housing_profile`. |
| Criterios de aceptación | Todas las vistas existen en DB viva; no contienen campos críticos todo `NULL`; tienen grano y columnas documentadas; son multi-municipio cuando sea posible. |

### Fase 2 — Rehacer semantic catalog sobre esas vistas

| Elemento | Detalle |
|---|---|
| Archivos | Reescribir `backend/app/ask/semantic_catalog.yaml`; eliminar o aislar `approved_metrics` legado. |
| Entregables | Catálogo único con métricas, sinónimos, entidades, operaciones, campos y caveats. |
| Criterios de aceptación | Cada métrica apunta a una vista existente; cada operación tiene builder/tool; tests validan todas las métricas configuradas. |

### Fase 3 — Crear Tool Layer universal

| Elemento | Detalle |
|---|---|
| Archivos | Crear `backend/app/ask/tools/agent_tools.py`, `backend/app/ask/tools/query_specs.py`; reducir one-off SQL en `sql_generator.py`. |
| Entregables | Tools reutilizables: ranking, aggregate, compare_years, age_cohort, electoral_summary, correlation, profile. |
| Criterios de aceptación | Las preguntas de la biblioteca se mapean a tools o se marcan explícitamente como no soportadas. |

### Fase 4 — Añadir OpenAI tool calling como planner real

| Elemento | Detalle |
|---|---|
| Archivos | `backend/app/ask/service.py`, `backend/app/ask/interpreter`, nuevo prompt de planner. |
| Entregables | LLM selecciona herramientas sobre catálogo estable; no genera SQL libre; devuelve plan y síntesis. |
| Criterios de aceptación | Logs muestran plan, tools llamadas, datos usados y verificación; coste/timeout/tool-call limit operativo. |

### Fase 5 — Añadir conversación persistente

| Elemento | Detalle |
|---|---|
| Archivos | Nueva tabla `core.agent_conversations` / `core.agent_turns`; modificar `conversation_store.py`. |
| Entregables | Memoria por usuario/sesión con TTL, resumen, entidades, métricas y años. |
| Criterios de aceptación | Sobrevive reload y restart; no mezcla usuarios; follow-ups reproducibles. |

### Fase 6 — Test suite

| Elemento | Detalle |
|---|---|
| Archivos | Expandir `backend/tests/ask`; añadir golden tests desde `askSocTraceTests.ts`; añadir checks de vistas DB. |
| Entregables | Tests por categoría, operación, tool, renderer y memoria. |
| Criterios de aceptación | Cada CTA preconfigurada es `OK`, `No soportada` explícita o retirada; no hay prompts aspiracionales invisibles. |

### Fase 7 — Renderizado y UX de agente

| Elemento | Detalle |
|---|---|
| Archivos | `AskSocTracePanel.tsx`, `askSocTraceService.ts`, chart components. |
| Entregables | Contrato fuerte de `chartSpec`, tabla con etiquetas humanas, streaming/typewriter, errores en español, debug controlado. |
| Criterios de aceptación | No se muestran códigos técnicos innecesarios; respuestas aparecen progresivamente; tablas y gráficos coinciden con la pregunta. |

## Conclusión

Ask SocTrace ya contiene piezas valiosas: datos internos, SQL seguro básico, memoria conversacional inicial, tools OpenAI y varios casos demográficos/electorales resueltos. El problema principal es de arquitectura: las capacidades están dispersas entre catálogo, handlers one-off, tools, repositorio legacy y vistas parcialmente aplicadas. Antes de construir el Municipal Intelligence Agent v1 conviene estabilizar primero el contrato de datos (`agent_` views), después unificar catálogo y tools, y solo entonces convertir el LLM en planner/sintetizador fiable.

## 13. Fase 1A ejecutada — Agent Data Layer Stabilization

Fecha de ejecución: 2026-06-08.

### Nuevas vistas canónicas creadas

| Vista | Estado en DB viva | Filas Mijas | Observaciones |
|---|---|---:|---|
| `marts.agent_section_lookup` | Creada | 37 | Lookup estable de secciones actuales con nombres legibles. |
| `marts.agent_population_age` | Creada | 7.602 | Población por sección, año, género y cohorte; conserva detalle H/M. |
| `marts.agent_section_profile` | Creada | 181 | Vista canónica sobre `marts.agent_section_profile_base`, materializada internamente para rendimiento. |
| `marts.agent_electoral_results` | Creada | 7.082 | Resultados normalizados por sección, elección y partido. |
| `marts.agent_electoral_summary` | Creada | 394 | Resumen por sección/elección con ganador, segundo partido, abstención, participación y margen. |
| `marts.agent_income_sources` | Creada | 165 | Renta y fuentes de ingresos 2019-2023. |
| `marts.agent_housing_profile` | Creada | 37 | Indicadores de vivienda/entorno construido disponibles en 2023. |

### Cambios de catálogo y generación SQL

| Elemento | Resultado |
|---|---|
| Catálogo semántico | Métricas centrales migradas a `marts.agent_*`; ya no apuntan a vistas `ask_*` ausentes para renta, vivienda o electoral. |
| Generador SQL semántico | Rankings de población, edad, renta, vivienda, abstención, voto y ganadores usan la capa `agent_*` cuando corresponde. |
| Contrato de columnas | Se normaliza `section_id` como columna técnica canónica en las vistas del agente. |

### Validación ejecutada

| Check | Resultado |
|---|---|
| Script SQL aplicado | `psql -d mijas -f sql/marts/030_agent_data_layer.sql` ejecutado correctamente. |
| QA SQL | `sql/qa/030_validate_agent_data_layer.sql` ejecutado correctamente. |
| Script Python | `backend/scripts/validate_agent_data_layer.py` ejecutado correctamente. |
| Tests Ask | `python -m unittest discover -s tests/ask` ejecutado correctamente: 32 tests OK, 1 skipped. |

Métricas clave no nulas en Mijas:

| Métrica | Filas no nulas |
|---|---:|
| `agent_section_profile.population_total` | 181 |
| `agent_section_profile.average_age` | 181 |
| `agent_section_profile.population_over_65` | 181 |
| `agent_section_profile.abstention_pct` | 179 |
| `agent_section_profile.winner_party` | 179 |
| `agent_electoral_results.vote_pct` | 7.082 |
| `agent_income_sources.income_individual` | 165 |
| `agent_income_sources.pension_share` | 165 |
| `agent_housing_profile.market_price_estimated_m2` | 37 |
| `agent_housing_profile.residential_pressure_index` | 37 |

### Limitaciones restantes

| Limitación | Impacto | Recomendación |
|---|---|---|
| Cobertura principal Mijas | La estructura es multi-municipio, pero la población real validada es Mijas. | Cargar/validar otros municipios antes de prometer multi-municipio operativo. |
| Vivienda solo 2023 | Preguntas temporales de vivienda no deben simular evolución. | Responder con caveat o crear futuras series cuando existan fuentes. |
| Renta 2019-2023 | No cubre 2024-2025. | Mantener caveat temporal en respuestas de renta. |
| `agent_section_profile_base` requiere refresh | Si cambian fuentes, la vista canónica puede quedar desactualizada. | Añadir job o paso ETL de `REFRESH MATERIALIZED VIEW marts.agent_section_profile_base`. |
| Aún existen definiciones legacy `ask_*` | No se han borrado para no romper dashboard o código antiguo. | Fase 1B/2: aislar legacy y retirar dependencias semánticas restantes. |

### Siguiente fase recomendada

Fase 1B / Fase 2: rehacer el catálogo semántico sobre el contrato `agent_*` como fuente única, separando métricas soportadas, pendientes y no soportadas; después crear una tool layer universal para rankings, agregaciones municipales, cohortes de edad, evolución temporal, electoral y vivienda.

## 14. Fase 2 ejecutada — Semantic Layer v2

Fecha de ejecución: 2026-06-08.

### Métricas migradas

El catálogo `backend/app/ask/semantic_catalog.yaml` queda en `version: 2` y usa solo vistas aprobadas `marts.agent_*`. Se migraron métricas de población, edad, renta, fuentes de ingresos, comportamiento electoral, ganador persistente, participación, abstención, margen competitivo, vivienda y entorno construido.

No hay métricas v2 soportadas apuntando a `marts.ask_*`.

### Operaciones soportadas

| Operación | Estado | Notas |
|---|---|---|
| `rank_sections` | Soportada | Rankings y extremos por sección. |
| `aggregate_municipality` | Soportada | Totales municipales y agregaciones simples de edad. |
| `compare_years` | Soportada | Comparación temporal de edad media y métricas compatibles. |
| `party_strength` | Soportada | Fortaleza electoral por partido. |
| `persistent_winner` | Soportada | Secciones donde un partido gana de forma persistente. |
| `historical_party_average` | Soportada | Media histórica electoral básica. |
| `age_cohort_projection` | Soportada | Proyección determinista de nuevos votantes desde `agent_population_age`. |
| `population_growth` | Soportada | Crecimiento por zonas históricas con lineage. |
| `cross_metric_ranking` | Beta | Score compuesto por percentiles; no causal. |

Catalogadas pero no expuestas como MVP completo: `filter_sections`, `section_profile`.

### Tests y validación

| Check | Resultado |
|---|---|
| Validación semántica | `python scripts/validate_semantic_layer_v2.py` OK. |
| Tests v2 | `backend/tests/ask/test_semantic_layer_v2.py` creado con la matriz de preguntas de Fase 2. |
| Tests semánticos legacy actualizados | `backend/tests/ask/test_semantic_layer.py` actualizado a nombres de operación v2. |
| SQL validator | Los planes soportados validan contra relaciones aprobadas `marts.agent_*`. |

### Frontend test library

`soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts` incorpora `status: "supported" | "beta" | "pending"`. El panel de tests oculta `pending` fuera de dev y los muestra deshabilitados si se habilitan en desarrollo.

### Pendientes

| Pendiente | Motivo |
|---|---|
| Correlaciones estadísticas genéricas | Quedan para planner/tool layer posterior. |
| Clustering y similitud | No pertenecen a Semantic Layer v2. |
| Predicción electoral | Requiere fase de planner/modelos. |
| Eliminación física de legacy `ask_*` | Fuera de alcance para no romper rutas antiguas. |

### Siguiente fase recomendada

Fase 3: construir una tool/query layer universal sobre las interpretaciones v2 para reducir SQL específico en `sql_generator.py`, exponer estados `supported/beta/pending` desde backend y preparar el futuro planner LLM sin añadir handlers one-off.

## 15. Fase 3 ejecutada — Universal Tool Layer

Fecha de ejecución: 2026-06-08.

### Tools creadas

Se crea `backend/app/ask/tools_v2/` con:

- `schemas.py`
- `registry.py`
- `executor.py`
- `sql_builders.py`
- `result_normalizer.py`
- `semantic_adapter.py`
- `errors.py`

Herramientas registradas:

- `rank_sections`
- `aggregate_municipality`
- `compare_years`
- `population_growth`
- `filter_sections`
- `section_profile`
- `party_strength`
- `persistent_winner`
- `historical_party_average`
- `age_cohort_projection`
- `cross_metric_ranking`
- `correlation_analysis`

### Operaciones soportadas

El servicio Ask SocTrace inicializado normalmente prefiere:

```txt
Semantic Layer v2 -> Tool Layer v2 -> ToolResult -> renderer
```

Las herramientas usan únicamente vistas `marts.agent_*` y pasan por `SqlValidator`.

### Beta tools

| Tool | Estado | Caveat |
|---|---|---|
| `cross_metric_ranking` | Beta | Score por percentiles; no prueba causalidad. |
| `correlation_analysis` | Beta | Correlación ecológica por sección; no causal. |

### Tests añadidos

| Archivo | Cobertura |
|---|---|
| `backend/tests/ask/test_tools_v2.py` | Tests directos de cada herramienta y schemas OpenAI. |
| `backend/tests/ask/test_semantic_to_tools_v2.py` | Camino pregunta -> semántica -> tool input -> ToolResult. |

### Limitaciones restantes

| Limitación | Recomendación |
|---|---|
| Renderizado v2 aún convive con renderizado semántico legado. | Consolidar renderer en Fase 4. |
| `section_profile` usa resolución determinista simple. | Añadir resolver universal de entidades antes del planner. |
| Correlación y scores son exploratorios. | Etiquetar como beta en UI/API hasta tener metodología más robusta. |
| SQL builder aún vive dentro de tools. | Extraer query specs reutilizables si crece la superficie. |

### Siguiente fase recomendada

Fase 4: construir renderer universal de `ToolResult`, publicar metadata de capacidades al frontend y preparar el contrato de tool calling para el futuro planner OpenAI sin permitir SQL libre.

## 16. Fase 4.1 ejecutada — LLM Provider abstracto

Fecha de ejecución: 2026-06-08.

### Archivos creados

- `backend/app/ask/llm/__init__.py`
- `backend/app/ask/llm/schemas.py`
- `backend/app/ask/llm/provider.py`
- `backend/app/ask/llm/factory.py`
- `backend/app/ask/llm/mock_provider.py`
- `backend/app/ask/llm/errors.py`
- `backend/tests/ask/test_llm_provider.py`
- `docs/llm_provider_layer.md`

### Contrato de proveedor

Se define `LLMProvider` con tres responsabilidades:

- `plan()` decide qué herramienta analítica debería llamarse.
- `synthesize()` convierte un `ToolResult` en una respuesta natural.
- `healthcheck()` informa si el proveedor está configurado.

El proveedor no ejecuta SQL ni accede a base de datos.

### Mock provider

`MockLLMProvider` permite pruebas locales sin claves externas. Incluye reglas deterministas mínimas para población, edad, jubilados y ganador persistente.

### Settings añadidos

Se añaden variables backend para `LLM_PROVIDER`, Gemini y OpenAI. El valor por defecto es `mock`.

### Integración

Ask SocTrace puede instanciar el proveedor y consultar su estado sin reemplazar el flujo actual. Se añade el healthcheck `/api/ask/llm/health`.

### Tests añadidos

`backend/tests/ask/test_llm_provider.py` cubre factory, schemas, provider contract, mock plan/synthesis, healthcheck y errores explícitos para `gemini`/`openai`.

### Siguiente paso recomendado

Fase 4.2: implementar `GeminiProvider` sobre este contrato, con tool calling controlado hacia Universal Tool Layer y tests con cliente mockeado, sin permitir SQL libre.

## 17. Fase 4.2 ejecutada — GeminiProvider

Fecha de ejecución: 2026-06-08.

### Archivos creados

- `backend/app/ask/llm/gemini_provider.py`
- `backend/app/ask/llm/gemini_schema_adapter.py`
- `backend/app/ask/llm/prompts.py`
- `backend/tests/ask/test_gemini_provider.py`
- `backend/scripts/test_gemini_provider_live.py`
- `docs/gemini_provider.md`

### SDK dependency

Se añade `google-genai` a `backend/requirements.txt`, usando el SDK oficial actual de Gemini.

### Estado del proveedor

`GeminiProvider` implementa:

- `plan()` con function calling.
- `synthesize()` desde `ToolResult`.
- `healthcheck()` sin llamada externa.
- selección de modelo por complejidad.
- guardia básica de consistencia numérica.

Gemini no accede a base de datos, no ejecuta SQL y no recibe claves desde frontend.

### Tests añadidos

`backend/tests/ask/test_gemini_provider.py` cubre configuración, healthcheck, routing de modelos, adaptación de schemas, parsing de function calls, síntesis estructurada, fallback a texto y ausencia de `GEMINI_API_KEY` en frontend.

### Siguiente fase recomendada

Integrar explícitamente `GeminiProvider` en el loop de Ask SocTrace:

```txt
AskSocTraceService -> LLMProvider.plan() -> ToolLayerV2.execute() -> LLMProvider.synthesize()
```

Mantener el fallback semántico determinista mientras se valida coste, latencia y precisión.

## 18. Fase 4.3 ejecutada — Complexity Router

Fecha de ejecución: 2026-06-08.

### Archivos creados

- `backend/app/ask/llm/complexity_router.py`
- `backend/tests/ask/test_complexity_router.py`

### Scoring rules

El router clasifica preguntas en:

- `simple`
- `semi_complex`
- `complex`

Usa scoring determinista por señales:

- consultas directas y rankings simples quedan en `simple`.
- comparaciones temporales, cohortes, D'Hondt, filtros y combinaciones deterministas suben a `semi_complex`.
- estrategia, recomendación, diagnóstico, correlación, clustering, predicción, índices y causalidad suben a `complex`.

También puede usar `semantic_interpretation` cuando existe, mapeando operaciones v2 como `rank_sections`, `compare_years`, `age_cohort_projection`, `cross_metric_ranking` o `correlation_analysis` al nivel adecuado.

### Integración

`AskSocTraceService` instancia `ComplexityRouter` sin cambiar todavía el flujo principal. El script live de Gemini ya pasa `complexity` en `LLMPlanRequest`.

### Test results

`backend/tests/ask/test_complexity_router.py` cubre ejemplos simples, semi-complejos, complejos y overrides semánticos.

### Siguiente fase recomendada

Exportar herramientas v2 como Gemini function declarations y conectar el loop:

```txt
ComplexityRouter -> LLMProvider.plan() -> ToolLayerV2.execute() -> LLMProvider.synthesize()
```

Mantener logs de debug con `complexity_score` y `complexity_reasons` para controlar coste y calidad.

## 19. Fase 4.4 ejecutada — Export Tools v2 to Gemini Schema

Fecha de ejecución: 2026-06-08.

### Adapter creado

Se refuerza `backend/app/ask/llm/gemini_schema_adapter.py` con:

- `normalize_json_schema_for_gemini()`
- `validate_llm_tool_schema()`
- `to_gemini_function_declaration()`
- `to_gemini_tools()`
- `parse_gemini_function_call()`

El adaptador convierte schemas genéricos `LLMToolSchema` a Gemini Function Declarations sin exponer SQL ni vistas internas.

### Tools exportadas

`backend/app/ask/tools_v2/registry.py` incorpora:

- `ToolDefinition`
- `BaseTool.llm_schema()`
- `get_llm_tool_schemas(include_beta=True)`

Se exportan tools con estado `supported` y `beta`; las `pending` quedan excluidas. La salida es determinista y ordenada por nombre.

Tools visibles para LLM:

- `age_cohort_projection`
- `aggregate_municipality`
- `compare_years`
- `correlation_analysis` beta
- `cross_metric_ranking` beta
- `filter_sections`
- `historical_party_average`
- `party_strength`
- `persistent_winner`
- `population_growth`
- `rank_sections`
- `section_profile`

### Tests añadidos

`backend/tests/ask/test_gemini_tool_schema_adapter.py` cubre normalización de JSON Schema, conversión a Gemini declarations, validación de schemas, export registry, exclusión de pending, parsing de function calls mockeados, integración de `GeminiProvider.plan()` con el adaptador y snapshot ligero determinista.

### Limitaciones restantes

Todavía no se conecta el loop completo Gemini planner -> Tool Layer v2 -> synthesis. Esta fase solo prepara los schemas y parsing seguros.

### Siguiente fase recomendada

Conectar el planner loop:

```txt
ComplexityRouter -> get_llm_tool_schemas() -> GeminiProvider.plan() -> ToolExecutorV2 -> GeminiProvider.synthesize()
```

Mantener fallback determinista y trazas de debug para validar coste, latencia y exactitud.

## 20. Fase 4.5 ejecutada — Gemini Planner Loop

Fecha de ejecución: 2026-06-08.

### Archivos creados

- `backend/app/ask/planner_loop.py`
- `backend/app/ask/answer_guard.py`
- `backend/tests/ask/test_gemini_planner_loop.py`
- `backend/scripts/test_gemini_planner_live.py`
- `docs/gemini_planner_loop.md`

### Settings añadidos

- `ask_use_llm_planner`
- `ask_llm_provider`
- `ask_llm_max_planning_attempts`
- `ask_llm_require_tool_for_numeric`
- `ask_llm_fallback_to_semantic_v2`
- `ask_llm_fallback_to_legacy`
- `ask_llm_debug`

Por defecto el planner LLM sigue apagado.

### Loop implementado

El flujo activo con `ASK_USE_LLM_PLANNER=true` es:

```txt
FollowUpResolver -> ComplexityRouter -> GeminiProvider.plan() -> ToolExecutorV2 -> AnswerGuard -> GeminiProvider.synthesize()
```

Gemini no recibe SQL ni ejecuta consultas. SocTrace valida tool name, argumentos y `ToolResult`.

### Guards

`AnswerGuard` bloquea respuestas que exponen SQL/vistas internas o contradicen de forma obvia la primera fila del `ToolResult`. Si falla la síntesis, se usa render determinista desde la herramienta.

### Tests añadidos

`backend/tests/ask/test_gemini_planner_loop.py` cubre:

- planificación simple
- pregunta numérica sin tool call
- tool inválida
- argumentos inválidos
- resultado vacío
- contradicción de síntesis
- follow-up sin llamar Gemini
- `persistent_winner`
- `age_cohort_projection`

### Siguiente fase recomendada

Probar el planner con Gemini real en entorno controlado, medir coste/latencia/calidad y añadir trazabilidad de auditoría por conversación antes de activarlo para usuarios MVP.

## 21. Fase 4.6 ejecutada — Tool Layer Execution

Fecha de ejecución: 2026-06-09.

### Executor creado

`backend/app/ask/tools_v2/executor.py` queda como frontera robusta de ejecución:

- valida nombre de herramienta contra `ToolRegistryV2`;
- rechaza herramientas desconocidas, `pending` o `hidden` sin debug;
- valida argumentos con modelos Pydantic;
- ejecuta la herramienta backend;
- normaliza y valida `ToolResult`;
- convierte fallos controlados en estados `unsupported` o `error`;
- registra latencia, estado, filas, métrica y municipio sin exponer secretos.

### Tools ejecutables

Quedan cubiertas end-to-end las herramientas núcleo:

- `rank_sections`
- `aggregate_municipality`
- `compare_years`
- `population_growth`
- `filter_sections`
- `section_profile`
- `party_strength`
- `persistent_winner`
- `historical_party_average`
- `age_cohort_projection`
- `cross_metric_ranking`
- `correlation_analysis` beta

La ejecución usa `SqlValidator` y `QueryExecutor`. Tool Layer v2 mantiene el contrato de no usar `marts.ask_*`, `core.*`, `raw.*` ni `staging.*`; las consultas se limitan a vistas `marts.agent_*` aprobadas.

### Resultados y errores

`ToolResult` incluye ahora `error_code` y `error_message`, además de metadata enriquecida para memoria conversacional:

- municipio;
- año o rango temporal;
- métrica y etiqueta;
- partido;
- tipo/año electoral;
- secciones devueltas.

Los errores técnicos se registran internamente y se transforman en mensajes limpios. Un fallo de validación SQL devuelve `status="error"` con `error_code="sql_validation_failed"`.

### Tests añadidos

Se añade `backend/tests/ask/test_tools_v2_execution.py`, cubriendo:

- casos positivos de las herramientas principales;
- resultados vacíos;
- herramienta desconocida;
- argumentos inválidos;
- herramienta pending;
- fallo de validación SQL convertido a `ToolResult`.

También se mantiene la compatibilidad con `test_tools_v2.py` y `test_gemini_planner_loop.py`.

### Limitaciones

- `correlation_analysis` sigue en beta.
- `cross_metric_ranking` es un índice territorial compuesto, no una relación causal.
- La ruta directa semántica conserva un puente síncrono (`execute_sync`) para no romper el comportamiento actual del dashboard.

### Siguiente fase recomendada

Integrar la síntesis Gemini y el render final de respuesta con telemetría de calidad, auditabilidad por conversación y pruebas con Gemini real antes de activar el planner para usuarios MVP.

## 22. Fase 4.7 ejecutada — Gemini Renderer

Fecha de ejecución: 2026-06-09.

### Archivos creados

Se crea `backend/app/ask/rendering/` con:

- `answer_contract.py`
- `renderer.py`
- `deterministic_renderer.py`
- `gemini_renderer.py`
- `answer_guard.py`
- `prompts.py`
- `followups.py`
- `__init__.py`

También se añade el script manual opcional:

- `backend/scripts/test_gemini_renderer_live.py`

### Comportamiento del renderer

`GeminiRenderer` recibe pregunta, `ToolResult`, contexto conversacional, estilo y locale. Antes de llamar al proveedor comprime el resultado con `compress_tool_result_for_llm()`, enviando solo resumen, primeras filas, metadata segura, metodología, caveats, follow-ups y resumen de chart.

Gemini se invoca solo mediante la abstracción:

```txt
provider.synthesize(LLMSynthesisRequest)
```

La salida se normaliza como `AskRenderedAnswer` y después se convierte a `AskResponse` compatible con el dashboard.

### Guard behavior

`RenderAnswerGuard` rechaza respuestas que:

- exponen SQL o nombres internos (`marts.`, `core.`, `raw.`, `staging.`, `SQLAlchemy`, `psycopg`, `Traceback`);
- contradicen la sección principal;
- introducen otro valor numérico evidente;
- omiten año o partido cuando son contexto clave;
- omiten entidades cuando la lista es corta y completa.

Si Gemini falla o no pasa el guard, SocTrace usa `DeterministicRenderer`. SocTrace calcula; Gemini explica.

### Contrato de frontend

El renderer preserva:

- `answer`;
- `shortCaveat`;
- `methodology`;
- `caveats`;
- `suggestedFollowUps`;
- `entities`;
- `table`;
- `chartSpec`;
- `data.metadata`.

`chartSpec` siempre procede de `ToolResult`; Gemini no lo modifica.

### Tests añadidos

Se añaden:

- `backend/tests/ask/test_gemini_renderer.py`
- `backend/tests/ask/test_answer_guard.py`

Cubren renderizado de ranking, lista de entidades, valor único, síntesis estructurada, texto plano, preservación de `chartSpec`, follow-ups separados y fallbacks por proveedor caído, SQL, sección incorrecta y lista incompleta.

### Siguiente fase recomendada

Persistir memoria conversacional enriquecida y activar el dashboard con el planner/render Gemini en entorno controlado, midiendo latencia, coste y tasa de fallback.

## 23. Fase 4.8 ejecutada — Memoria conversacional persistente

Fecha de ejecución: 2026-06-09.

### Tablas creadas

Se añade la migración:

- `sql/core/030_agent_conversation_memory.sql`

Tablas:

- `core.agent_conversations`
- `core.agent_turns`

Incluyen índices por sesión, usuario, actividad, conversación, métrica, herramienta y GIN sobre `sections`/`result_rows`.

### Backend store creado

Se añaden:

- `backend/app/ask/conversation/persistent_store.py`
- `backend/app/ask/conversation/schemas.py`

API principal:

- `get_or_create_conversation()`
- `append_user_turn()`
- `append_assistant_turn()`
- `get_context()`
- `clear_conversation()`
- `delete_inactive(days=30)`

La store limita `result_rows` a 50 filas y marca truncado en `summary` cuando procede.

### Integración backend

`AskSocTraceService` hidrata el `ConversationState` desde memoria persistente al inicio de la petición. Si las tablas no existen aún, hace rollback y vuelve a memoria en proceso.

`AskPlannerLoop` puede usar la store persistente para:

- crear/recuperar conversación por `session_id`;
- añadir turno de usuario;
- leer contexto antes de planificar;
- guardar turno de asistente con `ToolResult`, `AskRenderedAnswer` y metadata del planner.

`FollowUpResolver` reutiliza la estructura existente y ahora también responde listados como `¿Y esas secciones?` desde secciones persistidas.

### Frontend session behavior

El frontend ya mantiene sesión estable en:

```txt
soctrace.ask.session_id
```

Se envía ahora también `session_id` junto a `conversationId`. Los clicks en CTAs sugeridas usan el mismo hook y conservan la sesión.

### Tests añadidos

Se añade:

- `backend/tests/ask/test_persistent_conversation_memory.py`

Cubre:

- creación y reutilización por `session_id`;
- separación de sesiones;
- turnos de usuario/asistente;
- incremento de `turn_index`;
- metadata de `ToolResult`;
- recuperación de contexto;
- resolución de follow-up desde contexto persistido;
- simulación de reload con nueva store;
- límite de 50 filas;
- aislamiento por sesión.

### Limitaciones

- La limpieza TTL existe como helper, pero no se ejecuta automáticamente.
- El endpoint debug solo está disponible con `APP_ENV=development` y `ASK_DEBUG_ENABLED=true`.
- La migración debe aplicarse en la base de datos para activar persistencia real; antes de eso el backend conserva fallback en memoria.

### Siguiente fase recomendada

Activación controlada del dashboard y QA end-to-end: aplicar migración, probar reload/restart reales, medir latencia del planner/render, revisar tasa de fallback y validar CTAs sugeridas con usuarios MVP.

## 24. Fase 4.9 ejecutada — Integración Frontend

Fecha de ejecución: 2026-06-09.

### Frontend conectado al agente real

El panel Ask SocTrace usa ahora el endpoint versionado:

```txt
POST /api/v1/ask
```

Archivos modificados:

- `soctrace-web/src/lib/api.ts`
- `soctrace-web/src/features/ask-soctrace/services/askSocTraceService.ts`
- `soctrace-web/src/features/ask-soctrace/hooks/useAskSocTrace.ts`
- `soctrace-web/src/features/ask-soctrace/components/AskSocTracePanel.tsx`
- `soctrace-web/src/features/ask-soctrace/types/index.ts`
- `soctrace-web/src/components/layout/RightSidebar.tsx`

### Sesión y conversación

El frontend conserva:

- `soctrace.ask.session_id`
- `soctrace.ask.conversation_id`

Cada petición envía `sessionId/session_id` y, cuando existe, `conversationId/conversation_id`. Los clicks en CTAs sugeridas y tests predefinidos reutilizan la misma sesión.

### Respuesta y CTAs

El servicio normaliza camelCase y snake_case:

- respuesta textual;
- `shortCaveat`;
- metodología;
- caveats;
- suggested follow-ups;
- entidades;
- tabla;
- `chartSpec`;
- ids de conversación.

Las suggested follow-ups se muestran como botones solo en la última respuesta del asistente para evitar ruido en el historial.

### Panel derecho

`chartSpec` actualiza `askChart` cuando `type/kind !== "none"`.

Tipos soportados:

- `metric`;
- `bar`;
- `line`;
- `scatter`;
- `table`;
- `map` como fallback de lista/tabla.

### Estados UX

Se añade placeholder de carga:

```txt
SocTrace está analizando los datos...
```

Los errores de usuario se muestran en español limpio y no exponen trazas, SQL ni errores de proveedor.

### Debug

Los metadatos técnicos quedan ocultos en producción. El adapter solo propaga debug en desarrollo si:

```txt
VITE_ASK_SOCTRACE_DEBUG=true
```

### Tests y verificación

No hay framework de tests frontend configurado. La verificación de frontend se hace con:

```txt
npm run build
```

También se ejecutaron tests backend de planner/memoria persistente para confirmar la compatibilidad de sesión.

### Limitaciones

- `map` chart specs todavía no resaltan secciones en el mapa; se muestran como lista/tabla.
- Los gráficos del panel derecho son renderizadores ligeros.
- Falta QA manual end-to-end con backend corriendo, Gemini real y migración aplicada.

### Siguiente fase recomendada

Activar el flujo completo en entorno controlado: aplicar migración, lanzar backend/frontend, probar preguntas reales, CTAs, reload, restart, panel derecho y métricas de latencia/fallback antes del MVP.

## Hotfix — Gemini Activation + Persistent Memory Migration

Fecha de ejecución: 2026-06-09.

### Objetivo

Activar de forma verificable el flujo completo:

```txt
Gemini Planner -> Tool Layer -> Renderer -> Persistent Memory -> Dashboard
```

sin desactivar Gemini ni memoria persistente.

### Cambios backend

Archivos añadidos:

- `backend/app/ask/diagnostics.py`
- `backend/scripts/check_agent_memory.py`
- `backend/scripts/apply_agent_memory_migration.py`
- `backend/scripts/check_gemini_sdk.py`
- `backend/scripts/test_gemini_connection.py`
- `backend/scripts/test_planner_loop.py`
- `backend/scripts/test_persistent_memory.py`

Archivos modificados:

- `backend/requirements.txt`
- `backend/app/ask/llm/gemini_provider.py`
- `backend/app/ask/llm/gemini_schema_adapter.py`
- `backend/app/ask/conversation/persistent_store.py`
- `backend/app/api/v1/routes/ask.py`
- `backend/app/main.py`

### Gemini SDK

Se fija dependencia oficial:

```txt
google-genai>=1.20.0,<2.0
```

`GeminiProvider` falla de forma explícita si falta el SDK e indica:

```txt
pip install google-genai
```

El adaptador de schemas mantiene diccionarios internos estables y deja que `google-genai` convierta tools/configuración a sus tipos propios.

### Memoria persistente

Se añade diagnóstico y aplicación idempotente de:

```txt
sql/core/030_agent_conversation_memory.sql
```

Tablas verificadas:

- `core.agent_conversations`
- `core.agent_turns`

El store corrige dos problemas de runtime:

- búsqueda de conversaciones con `user_id IS NULL` sin parámetros nulos ambiguos para PostgreSQL;
- escritura de JSONB usando `psycopg.types.json.Jsonb`.

### Health endpoint y startup diagnostics

Nuevo endpoint:

```txt
GET /api/v1/ask/llm/health
```

Payload saludable:

```json
{
  "provider": "gemini",
  "planner_enabled": true,
  "gemini_sdk": true,
  "api_key_loaded": true,
  "memory_tables": true,
  "tool_layer": true,
  "status": "healthy"
}
```

En arranque se registra el bloque:

```txt
SOC TRACE AI AGENT
Provider: gemini
Planner: enabled
Gemini SDK: OK
Memory tables: OK
Tool Layer: OK
```

### Verificación ejecutada

Comandos verificados:

```bash
python scripts/check_gemini_sdk.py
python scripts/check_agent_memory.py
python scripts/apply_agent_memory_migration.py
python scripts/test_gemini_connection.py
python scripts/test_planner_loop.py
python scripts/test_persistent_memory.py
```

Resultados clave:

- Gemini SDK: OK.
- Memoria: tablas OK.
- Migración: `already exists`.
- Conexión Gemini: Provider OK, Model OK, Response OK.
- Planner Loop: provider `gemini`, tool `rank_sections`, status `ok`.
- Persistent Memory: conversación creada y turnos almacenados.
- `/api/v1/ask/llm/health`: `status=healthy`.

Tests ejecutados:

```bash
python -m unittest tests/ask/test_gemini_provider.py tests/ask/test_persistent_conversation_memory.py
python -m unittest tests/ask/test_gemini_renderer.py tests/ask/test_answer_guard.py
```

### Limitaciones

Una ejecución amplia de `python -m unittest discover tests/ask` puede llamar al Gemini real si `.env` mantiene `LLM_PROVIDER=gemini` y `ASK_USE_LLM_PLANNER=true`; en ese caso puede aparecer cuota `429 RESOURCE_EXHAUSTED`. Para CI conviene aislar tests con provider mock o variables de entorno de test.

### Siguiente recomendación

Separar configuración de test/CI de la configuración local de activación Gemini y añadir un smoke test end-to-end con presupuesto controlado para no consumir cuota del modelo en cada ejecución amplia.

## MVP Optimization — Ask SocTrace Test Catalog

Fecha de ejecución: 2026-06-09.

### Objetivo

Convertir la “Lista de Tests” en una biblioteca de consultas de producto para Friend & Family MVP:

- ocultar estados internos `supported`, `beta` y `pending`;
- mostrar solo `Disponible` y `Próximamente`;
- activar toda consulta que ya puede resolverse con Agent Data Layer, Semantic Layer v2, Tool Layer v2 y SQL seguro;
- deshabilitar solo preguntas que requieren forecasting, transferencia de voto, clustering/ML o modelos de estrategia.

### Cambios frontend

Archivo principal:

```txt
soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts
```

Cambios:

- `status` pasa a `available | coming_soon`;
- cada consulta disponible incluye `tool` interno;
- se añaden consultas MVP que estaban descritas en producto pero no aparecían literalmente en el catálogo;
- se rebajan a `coming_soon` preguntas vagas de variable automática, distribución, outliers, clustering, predicción y optimización de campaña.

Render:

```txt
soctrace-web/src/components/layout/RightSidebar.tsx
```

UI visible:

- `● Disponible`: verde, CTA habilitada;
- `○ Próximamente`: muted, CTA deshabilitada;
- tooltip de futuro para consultas no disponibles.

Textos actualizados:

- título: `Consultas disponibles`;
- subtítulo: `Explora algunas de las preguntas que actualmente puede responder el agente SocTrace utilizando datos reales del municipio.`

### Cambios Tool Layer

Durante la validación aparecieron dos fallos reales y se corrigieron:

- `compare_years` usaba el nombre original de columna dentro del CTE agregado en vez del alias `metric_value`;
- `cross_metric_ranking` y `correlation_analysis` tenían joins temporales ambiguos cuando las tablas compartían columna `year`.

Archivo:

```txt
backend/app/ask/tools_v2/sql_builders.py
```

### Documentación y validación

Documentos generados:

- `docs/test_catalog_audit.md`
- `docs/test_catalog_available.md`

Script de validación:

```txt
backend/scripts/validate_mvp_test_catalog.py
```

Resultado del catálogo:

```txt
124 de 158 consultas visibles como Disponible (78,5%)
```

Validación smoke:

```txt
MVP catalog validation OK
```

Build frontend:

```txt
npm run build
```

Resultado: OK.

Tests backend focalizados:

```txt
python -m unittest tests/ask/test_tools_v2.py tests/ask/test_tools_v2_execution.py tests/ask/test_semantic_to_tools_v2.py
```

Resultado: OK.

### Limitaciones

Las consultas `Disponible` se validan por recetas Tool Layer representativas y por disponibilidad de datasets `marts.agent_*`. La ejecución natural final sigue dependiendo de que el planner Gemini seleccione la herramienta adecuada para cada formulación; el catálogo evita prompts que requieren modelos no implementados.

### Siguiente recomendación

Añadir un endpoint backend de catálogo ejecutable que exponga automáticamente solo prompts validados por Tool Layer, para que frontend y backend compartan una única fuente de verdad.
