# soctrace MVP Database Object Inventory

This inventory is for Supabase/Railway PROD readiness. It focuses on database objects required by the current MVP backend, dashboard, Ask soctrace, forecast endpoints and legacy Streamlit queries.

## Schemas

| Schema | Purpose | Required |
|---|---|---|
| `raw` | Raw imported files and source-shaped tables | Yes, for rebuild |
| `staging` | Normalized load buffers and temporary loader tables | Yes, for rebuild |
| `core` | Durable canonical tables used by services and marts | Yes |
| `marts` | Read models, views and materialized views used by the app | Yes |
| `qa` | QA/smoke queries | Optional in runtime, useful for deployment |

## Extensions

| Extension | Why |
|---|---|
| `postgis` | Required by geography columns, spatial indexes, `ST_AsGeoJSON`, `ST_Transform`, `ST_Area`, `ST_IsValid` |

## Runtime Critical Objects

These are the objects most directly tied to the current 500s:

| Object | Kind | Used by |
|---|---|---|
| `marts.v_mapa_seccion_2023` | View | `backend/app/db/sql/municipalities.sql`, legacy map queries |
| `marts.mijas_features_panel` | Materialized view | `backend/app/db/sql/municipalities.sql`, `geo_sections.sql`, `section_detail.sql`, Streamlit queries |
| `marts.v_mapa_seccion_anio` | View | `geo_sections.sql`, `geo_sections_bbox.sql`, `section_detail.sql` |
| `marts.mv_electoral_behavior` | Materialized view | Map electoral layer, analyst services, Ask soctrace |
| `marts.dim_seccion_display` | Table | Labels for dashboard, map, Ask soctrace |

## Raw Tables

| Object | Kind | Source script |
|---|---|---|
| `raw.demografia_genero_edad_2023` | Table | `sql/raw/001_create_raw_demografia_genero_edad_2023.sql` |
| `raw.renta_ine_2023` | Table | `sql/raw/002_create_raw_renta_ine_2023.sql` |
| `raw.elecciones_municipales_2019_mesa` | Table | `sql/raw/003_create_raw_elecciones_municipales_2019_mesa.sql` |
| `raw.demografia_genero_edad_multi_anio` | Table | `sql/raw/004_create_raw_demografia_genero_edad_multi_anio.sql` |
| `raw.renta_ine_2019_2023` | Table | `sql/raw/005_create_raw_renta_ine_2019_2023.sql` |
| `raw.fuentes_ingresos_2019_2023` | Table | `sql/raw/006_create_raw_fuentes_ingresos_2019_2023.sql` |
| `raw.ine_nivel_estudios_2021_2024` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_ocupacion_2021_2024` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_actividad_2021_2023` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_rama_actividad_2021_2023` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_sit_profesional_2021_2023` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_gini_p80p20_2015_2023` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |
| `raw.ine_fuente_ingresos_2019_2023` | Table | `sql/raw/007_create_raw_ine_socioeconomic.sql` |

## Staging Tables

| Object | Kind | Source script |
|---|---|---|
| `staging.fact_genero_edad` | Table | `sql/staging/001_create_staging_fact_genero_edad.sql` |
| `staging.renta_seccion_2023` | Table | `sql/staging/002_create_staging_renta_seccion_2023.sql` |
| `staging.manual_precio_m2_seccion_2023` | Table | `sql/staging/003_create_manual_precio_m2_seccion_2023.sql` |
| `staging.resultados_mesa_2019` | Table | `sql/staging/004_create_staging_resultados_mesa_2019.sql` |
| `staging.fact_genero_edad_multi_anio` | Table | `sql/staging/005_create_staging_fact_genero_edad_multi_anio.sql` |
| `staging.renta_seccion_multi_anio` | Table | `sql/staging/006_create_staging_renta_seccion_multi_anio.sql` |
| `staging.fuentes_ingresos_seccion` | Table | `sql/staging/007_create_staging_fuentes_ingresos_seccion.sql` |
| `staging.socioeconomic_indicator_section` | Table | `sql/staging/008_create_staging_socioeconomic_indicator_section.sql` |
| `staging.*_tmp` | Temporary loader tables | Created by ETL scripts during electoral/geography loads |

## Core Tables

| Object | Kind | Source |
|---|---|---|
| `core.election_type` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.election` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.candidatura` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.candidatura_alias` | Table | `sql/core/004_create_core_candidatura_alias.sql` |
| `core.mesa` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.datos_mesa` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.resultados_mesa` | Table | `sql/deploy/01_core_base_tables.sql` |
| `core.resultados_seccion` | Table | `sql/core/007_create_core_electoral_historical.sql` |
| `core.seccion` | Table | `sql/deploy/01_core_base_tables.sql`; legacy current-geometry compatibility |
| `core.seccion_historica` | Table | `sql/core/003_create_core_seccion_historica.sql` |
| `core.poblacion_edad` | Table | `sql/core/001_create_core_poblacion_edad.sql` |
| `core.renta_seccion` | Table | `sql/core/002_create_core_renta_seccion.sql` |
| `core.fuentes_ingresos_seccion` | Table | `sql/core/006_create_core_fuentes_ingresos_seccion.sql` |
| `core.socioeconomic_indicator_catalog` | Table | `sql/core/008_create_core_socioeconomic_indicators.sql` |
| `core.socioeconomic_indicator_section` | Table | `sql/core/008_create_core_socioeconomic_indicators.sql` |
| `core.agent_conversations` | Table | `sql/core/030_agent_conversation_memory.sql` |
| `core.agent_turns` | Table | `sql/core/030_agent_conversation_memory.sql` |
| `core.agent_audit_log` | Table | `sql/marts/023_electoral_forecasting_2027.sql` |
| `core.mijas_contextual_priors` | Table | `sql/marts/024_mijas_political_context_counterweights.sql` |
| `core.mijas_section_context` | Table | `sql/marts/024_mijas_political_context_counterweights.sql` |

## Marts Tables

| Object | Kind | Source |
|---|---|---|
| `marts.dim_seccion_display` | Table | `sql/marts/005_dim_seccion_display.sql` and `005b_seed_dim_seccion_display_mijas_2023.sql` |

## Marts Views

| Object | Kind | Source |
|---|---|---|
| `marts.v_mapa_seccion_anio` | View | `sql/marts/014_v_mapa_seccion_anio.sql` |
| `marts.v_mapa_seccion_2023` | View | `sql/deploy/03_prod_geography_compat_views.sql` |
| `marts.v_geografia_seccion` | View | `sql/deploy/03_prod_geography_compat_views.sql` |
| `marts.v_poblacion_seccion_anio` | View | `sql/marts/001_v_poblacion_seccion_anio.sql` |
| `marts.v_resultados_seccion_anio` | View | `sql/marts/002_v_resultados_seccion_anio.sql` |
| `marts.v_income_level` | View | `sql/marts/011_v_income_level.sql` |
| `marts.v_income_level_layer` | View | `sql/marts/011_v_income_level.sql` |
| `marts.v_population_layer` | View | `sql/marts/015_v_population_layer.sql` |
| `marts.v_mapa_age_structure` | View | `sql/marts/009_v_mapa_age_structure_2023.sql` |
| `marts.v_mapa_age_structure_2023` | View | `sql/marts/009_v_mapa_age_structure_2023.sql` |
| `marts.v_income_sources` | View | `sql/marts/017_v_income_sources.sql` |
| `marts.v_income_sources_profile` | View | `sql/marts/017_v_income_sources.sql` |
| `marts.v_resultados_seccion_eleccion` | View | `sql/marts/018_v_resultados_seccion_eleccion.sql` |
| `marts.v_socioeconomic_indicators` | View | `sql/marts/020_socioeconomic_intelligence.sql` |
| `marts.v_socioeconomic_profile` | View | `sql/marts/020_socioeconomic_intelligence.sql` |
| `marts.v_socioeconomic_intelligence_base` | View | `sql/marts/020_socioeconomic_intelligence.sql` |
| `marts.socioeconomic_intelligence_signals` | View | `sql/marts/020_socioeconomic_intelligence.sql` |
| `marts.ml_socioeconomic_section_panel` | View | `sql/marts/020_socioeconomic_intelligence.sql` |
| `marts.v_land_built_environment` | View | `sql/marts/021_v_land_built_environment.sql` |
| `marts.electoral_forecasting_municipality_2027` | View | `sql/marts/023_electoral_forecasting_2027.sql` |
| `marts.ask_section_lookup` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_population_age` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_population_age_range` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_income` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_electoral_results` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_electoral_summary` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_housing` | View | `sql/marts/026_ask_analytical_views.sql` |
| `marts.ask_section_profile` | View | `sql/marts/026_ask_analytical_views.sql` and later `027_ask_population_profile.sql` |
| `marts.ask_population_profile` | View | `sql/marts/027_ask_population_profile.sql` |
| `marts.agent_section_lookup` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_population_age` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_electoral_results` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_electoral_summary` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_income_sources` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_housing_profile` | View | `sql/marts/030_agent_data_layer.sql` |
| `marts.agent_section_profile` | View | `sql/marts/030_agent_data_layer.sql` |

## Marts Materialized Views

| Object | Kind | Source |
|---|---|---|
| `marts.mijas_features_panel` | Materialized view | `sql/marts/003_mijas_features_panel.sql` |
| `marts.mv_seccion_edad_media` | Materialized view | `sql/marts/008_mv_seccion_edad_media.sql`; optional legacy |
| `marts.mv_electoral_behavior` | Materialized view | `sql/marts/010_mv_electoral_behavior.sql` |
| `marts.territorial_intelligence_section_2023` | Materialized view | `sql/marts/012_territorial_intelligence_section_2023.sql` |
| `marts.housing_intelligence_features_2023` | Materialized view | `sql/marts/022_housing_intelligence_quality_life_2023.sql` |
| `marts.housing_intelligence_ui_2023` | Materialized view | `sql/marts/022_housing_intelligence_quality_life_2023.sql` |
| `marts.electoral_forecasting_features_2027` | Materialized view | `sql/marts/023_electoral_forecasting_2027.sql` |
| `marts.electoral_forecasting_ui_2027` | Materialized view | `sql/marts/023_electoral_forecasting_2027.sql` |
| `marts.electoral_forecast_counterweights_2027` | Materialized view | `sql/marts/024_mijas_political_context_counterweights.sql` |
| `marts.electoral_scenarios_2027` | Materialized view | `sql/marts/025_electoral_scenarios_2027.sql` |
| `marts.agent_section_profile_base` | Materialized view | `sql/marts/030_agent_data_layer.sql` |

## Dependency Summary

| Layer | Depends on | Produces |
|---|---|---|
| `raw` | External source files | Raw source-shaped tables |
| `staging` | `raw` and loader temp data | Normalized load buffers |
| `core` | `staging`, loader transforms, PostGIS | Durable demographics, elections, income, geography, memory |
| Foundation `marts` | `core` | `dim_seccion_display`, geography, population, election, income views |
| Dashboard `marts` | Foundation `marts` | `mijas_features_panel`, map layers, section detail, forecast and housing layers |
| Ask soctrace `marts` | Dashboard `marts` and `core` | `agent_*` views and `ask_*` views |

## Known PROD Failure Cause

The current Railway error:

```txt
relation "marts.v_mapa_seccion_2023" does not exist
relation "marts.mijas_features_panel" does not exist
```

means the app connected to Supabase successfully, but the mart layer was not recreated in PROD. Run the ordered deployment in `deployment_order.md`, especially `sql/deploy/04_marts_objects.sql`.
