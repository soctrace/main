-- soctrace MVP Supabase deployment validation.

WITH required_objects(schema_name, object_name, expected_kind) AS (
    VALUES
        ('core', 'poblacion_edad', 'table'),
        ('core', 'renta_seccion', 'table'),
        ('core', 'seccion_historica', 'table'),
        ('core', 'election', 'table'),
        ('core', 'candidatura_alias', 'table'),
        ('core', 'resultados_seccion', 'table'),
        ('core', 'agent_conversations', 'table'),
        ('core', 'agent_turns', 'table'),
        ('marts', 'dim_seccion_display', 'table'),
        ('marts', 'v_mapa_seccion_anio', 'view'),
        ('marts', 'v_mapa_seccion_2023', 'view'),
        ('marts', 'mijas_features_panel', 'materialized view'),
        ('marts', 'v_population_layer', 'view'),
        ('marts', 'v_mapa_age_structure', 'view'),
        ('marts', 'v_mapa_age_structure_2023', 'view'),
        ('marts', 'mv_electoral_behavior', 'materialized view'),
        ('marts', 'v_income_level_layer', 'view'),
        ('marts', 'v_income_sources_profile', 'view'),
        ('marts', 'v_land_built_environment', 'view'),
        ('marts', 'territorial_intelligence_section_2023', 'materialized view'),
        ('marts', 'housing_intelligence_features_2023', 'materialized view'),
        ('marts', 'electoral_forecasting_municipality_2027', 'view'),
        ('marts', 'electoral_forecasting_features_2027', 'materialized view'),
        ('marts', 'electoral_forecasting_ui_2027', 'materialized view'),
        ('marts', 'electoral_forecast_counterweights_2027', 'materialized view'),
        ('marts', 'electoral_scenarios_2027', 'materialized view'),
        ('marts', 'agent_section_lookup', 'view'),
        ('marts', 'agent_population_age', 'view'),
        ('marts', 'agent_electoral_results', 'view'),
        ('marts', 'agent_electoral_summary', 'view'),
        ('marts', 'agent_income_sources', 'view'),
        ('marts', 'agent_housing_profile', 'view'),
        ('marts', 'agent_section_profile_base', 'materialized view'),
        ('marts', 'agent_section_profile', 'view')
),
actual AS (
    SELECT
        n.nspname AS schema_name,
        c.relname AS object_name,
        CASE c.relkind
            WHEN 'r' THEN 'table'
            WHEN 'p' THEN 'table'
            WHEN 'v' THEN 'view'
            WHEN 'm' THEN 'materialized view'
            ELSE c.relkind::text
        END AS actual_kind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
)
SELECT
    r.schema_name,
    r.object_name,
    r.expected_kind,
    a.actual_kind,
    CASE WHEN a.object_name IS NULL THEN 'missing' ELSE 'ok' END AS status
FROM required_objects r
LEFT JOIN actual a
  ON a.schema_name = r.schema_name
 AND a.object_name = r.object_name
ORDER BY status DESC, r.schema_name, r.object_name;
