-- soctrace MVP Supabase deployment: marts in dependency order.
-- Run after data has been loaded into core/staging tables.

\ir ../marts/005_dim_seccion_display.sql
\ir ../marts/005b_seed_dim_seccion_display_mijas_2023.sql
\ir ../marts/014_v_mapa_seccion_anio.sql
\ir 03_prod_geography_compat_views.sql

\ir ../marts/001_v_poblacion_seccion_anio.sql
\ir ../marts/002_v_resultados_seccion_anio.sql
\ir ../marts/011_v_income_level.sql
\ir ../marts/003_mijas_features_panel.sql
\ir ../marts/004_mijas_features_panel_indexes.sql

\ir ../marts/015_v_population_layer.sql
\ir ../marts/009_v_mapa_age_structure_2023.sql
\ir ../marts/010_mv_electoral_behavior.sql
\ir ../marts/017_v_income_sources.sql
\ir ../marts/018_v_resultados_seccion_eleccion.sql
\ir ../marts/020_socioeconomic_intelligence.sql
\ir ../marts/021_v_land_built_environment.sql
\ir ../marts/012_territorial_intelligence_section_2023.sql
\ir ../marts/022_housing_intelligence_quality_life_2023.sql
\ir ../marts/023_electoral_forecasting_2027.sql
\ir ../marts/024_mijas_political_context_counterweights.sql
\ir ../marts/025_electoral_scenarios_2027.sql
\ir ../marts/026_ask_analytical_views.sql
\ir ../marts/027_ask_population_profile.sql
\ir ../marts/030_agent_data_layer.sql
