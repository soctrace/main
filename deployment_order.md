# soctrace MVP Database Deployment Order

This is the exact database recreation order for Supabase PROD. It is infrastructure-only and does not require application code changes.

## 0. Preconditions

Use a Supabase Postgres connection string with DDL privileges.

Run commands from repository root:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/00_extensions_and_schemas.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/01_core_base_tables.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/02_raw_staging_core_objects.sql
```

`postgis` must be available because map views use geometry columns and PostGIS functions.

## 1. Create Schemas And Base Tables

Order:

1. `sql/deploy/00_extensions_and_schemas.sql`
2. `sql/deploy/01_core_base_tables.sql`
3. `sql/deploy/02_raw_staging_core_objects.sql`

This creates:

- schemas: `raw`, `staging`, `core`, `marts`, `qa`
- raw/staging tables
- core demographic, income, geography, electoral, memory and base compatibility tables

## 2. Load Data Into Raw/Staging/Core

The SQL deployment files create objects, but they do not load source data.

Run the ETL/loaders against the Supabase `DATABASE_URL` in this order:

1. Geography:
   - `etl/geography/load_secciones_historicas.py`
   - required output: `core.seccion_historica`
2. Demography:
   - `etl/demography/load_population_multi_year.py`
   - required output: `core.poblacion_edad`
3. Income:
   - `etl/economic/load_renta_ine_multi_year.py`
   - `etl/economic/load_fuentes_ingresos_multi_year.py`
   - required output: `core.renta_seccion`, `core.fuentes_ingresos_seccion`
4. Socioeconomic indicators:
   - `etl/economic/load_socioeconomic_indicators.py`
   - required output: `core.socioeconomic_indicator_catalog`, `core.socioeconomic_indicator_section`
5. Electoral:
   - `etl/electoral/load_official_mesa_zip.py`
   - `etl/electoral/load_andaluzas_2018_csv.py`
   - `etl/electoral/load_andaluzas_section_csv.py`
   - `etl/electoral/load_andaluzas_2026_xls.py`
   - required output: `core.election`, `core.candidatura`, `core.candidatura_alias`, `core.mesa`, `core.datos_mesa`, `core.resultados_mesa`, `core.resultados_seccion`
6. Real estate / built environment:
   - `etl/real_estate/load_manual_section_prices.py`
   - `etl/catastro/load_catastro_stats.py`
   - `etl/catastro/load_cp_gml_to_postgis.py`
   - `etl/catastro/load_bu_gml_to_postgis.py`
   - required output: staging/catastro tables consumed by housing and land-built marts

If PROD is being seeded from an existing local database dump, restore the data before step 3.

## 3. Build Marts

Run:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/04_marts_objects.sql
```

This builds the MVP marts in dependency order:

1. Section display:
   - `marts.dim_seccion_display`
2. Geography:
   - `marts.v_mapa_seccion_anio`
   - `marts.v_geografia_seccion`
   - `marts.v_mapa_seccion_2023`
3. Population, election and income foundations:
   - `marts.v_poblacion_seccion_anio`
   - `marts.v_resultados_seccion_anio`
   - `marts.v_income_level`
   - `marts.v_income_level_layer`
4. Dashboard panel:
   - `marts.mijas_features_panel`
5. Map/analysis layers:
   - `marts.v_population_layer`
   - `marts.v_mapa_age_structure`
   - `marts.v_mapa_age_structure_2023`
   - `marts.mv_electoral_behavior`
   - `marts.v_income_sources`
   - `marts.v_income_sources_profile`
   - `marts.v_resultados_seccion_eleccion`
   - `marts.v_socioeconomic_*`
   - `marts.socioeconomic_intelligence_signals`
   - `marts.v_land_built_environment`
   - `marts.territorial_intelligence_section_2023`
   - `marts.housing_intelligence_features_2023`
   - `marts.housing_intelligence_ui_2023`
6. Forecast:
   - `marts.electoral_forecasting_features_2027`
   - `marts.electoral_forecasting_ui_2027`
   - `marts.electoral_forecasting_municipality_2027`
   - `marts.electoral_forecast_counterweights_2027`
   - `marts.electoral_scenarios_2027`
7. Ask soctrace semantic layer:
   - `marts.ask_*`
   - `marts.agent_*`

## 4. Validate Required Objects

Run:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/deploy/99_validate_mvp_objects.sql
```

Every row should return `status = ok`.

Minimum smoke checks for the failing endpoints:

```sql
SELECT COUNT(*) FROM marts.v_mapa_seccion_2023;
SELECT COUNT(*) FROM marts.mijas_features_panel;
SELECT COUNT(*) FROM marts.v_mapa_seccion_anio WHERE anio = 2023;
SELECT COUNT(*) FROM marts.mv_electoral_behavior;
```

Expected MVP shape for Mijas:

- `marts.v_mapa_seccion_2023`: non-empty
- `marts.mijas_features_panel`: non-empty, normally one row per Mijas section/year/election available
- `marts.v_mapa_seccion_anio WHERE anio = 2023`: non-empty

## 5. Endpoint Readiness

After validation, Railway endpoints should stop failing with `UndefinedTable`:

```txt
GET /api/v1/municipalities
GET /api/v1/geo/sections?municipality_id=29070&year=2023
```

Note: the backend route currently validates `municipality_id` as exactly 5 chars. Use `29070`, not `mijas`, for `/api/v1/geo/sections`.

## Dependency Graph

```txt
raw
  -> staging
    -> core.poblacion_edad
    -> core.renta_seccion
    -> core.fuentes_ingresos_seccion
    -> core.socioeconomic_indicator_*
    -> core.seccion_historica
    -> core.election / candidatura / resultados_*
      -> marts.dim_seccion_display
      -> marts.v_mapa_seccion_anio
      -> marts.v_geografia_seccion
      -> marts.v_mapa_seccion_2023
      -> marts.v_poblacion_seccion_anio
      -> marts.v_resultados_seccion_anio
      -> marts.v_income_level_layer
        -> marts.mijas_features_panel
        -> marts.v_population_layer
        -> marts.v_mapa_age_structure*
        -> marts.mv_electoral_behavior
        -> marts.v_income_sources_profile
        -> marts.socioeconomic_intelligence_signals
        -> marts.v_land_built_environment
        -> marts.territorial_intelligence_section_2023
        -> marts.housing_intelligence_*
        -> marts.electoral_forecasting_*
        -> marts.ask_*
        -> marts.agent_*
```

## Files Added For Deployment

| File | Purpose |
|---|---|
| `sql/deploy/00_extensions_and_schemas.sql` | PostGIS and schemas |
| `sql/deploy/01_core_base_tables.sql` | Core base tables that ETL previously created implicitly |
| `sql/deploy/02_raw_staging_core_objects.sql` | Existing raw/staging/core DDL bundle |
| `sql/deploy/03_prod_geography_compat_views.sql` | PROD-safe geography compatibility views |
| `sql/deploy/04_marts_objects.sql` | Ordered marts build |
| `sql/deploy/99_validate_mvp_objects.sql` | Required object validation |
| `sql/deploy/deploy_all.psql` | Entrypoint for schema/base setup |
