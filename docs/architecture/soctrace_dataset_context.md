# SocTrace Dataset Schema Context

## Important Principles

- `seccion_id` is the canonical territorial key.
- marts are the analytical source for frontend/API.
- no frontend should directly consume raw/staging.
- all strategic scores are comparative indexes, not absolute truths.
- percentages should explicitly define scale: 0-1 ratio vs 0-100 percentage/score.
- avoid hardcoded municipality assumptions outside display labels.
- geometry for map-facing marts should be EPSG:4326.
- destructive database changes must be avoided unless explicitly approved.

## Project Context

Project: `SocTrace`

Current municipality focus: Mijas, Spain.

Canonical database: PostgreSQL/PostGIS database `mijas`.

Main analytical unit: census section / electoral section.

Canonical section key: `seccion_id`.

`seccion_id` format:

- 10-digit text key.
- Built as: `cod_provincia` (2) + `cod_municipio` (3) + `cod_distrito` (2) + `cod_seccion` (3).
- Mijas municipality id: `29070`.
- Example shape: `2907001019`.

Current production coverage:

- 37 Mijas sections in `core.seccion`.
- 37 sections in `marts.v_mapa_seccion_2023`.
- 37 rows in `marts.mijas_features_panel`.
- 37 rows in `marts.territorial_intelligence_section_2023`.
- Catastro parcels loaded: about 27,964 in `staging.catastro_cp_mijas`.
- Catastro building parts loaded: about 84,593 in `staging.catastro_bu_mijas`.

## Schema Layers

### raw

Preserves original source-shaped data.

Important tables:

- `raw.demografia_genero_edad_2023`
- `raw.renta_ine_2023`

Target tables mentioned in the relational model:

- `raw.geo_seccion_YYYY`
- `raw.demografia_genero_edad_YYYY`
- `raw.demografia_genero_pais_YYYY`
- `raw.elect_candidaturas_YYYY`
- `raw.elect_datos_mesa_YYYY`
- `raw.elect_resultados_mesa_YYYY`
- `raw.elect_resultados_municipio_YYYY`
- `raw.encuesta_<nombre>_<YYYY>`

### staging

Technical normalization and source-specific intermediate tables.

Important tables:

- `staging.seccion_geo`
- `staging.fact_genero_edad`
- `staging.renta_seccion_2023`
- `staging.candidatura_raw`
- `staging.datos_mesa_raw`
- `staging.resultados_mesa_raw`
- `staging.resultados_municipio_raw`
- `staging.manual_precio_m2_seccion_2023`
- `staging.catastro_cp_raw`
- `staging.catastro_bu_raw`
- `staging.catastro_cp_mijas`
- `staging.catastro_bu_mijas`
- `staging.catastro_valor_distrito_mijas_2023`
- `staging.vivienda_valor_tasado_mijas_2023`

Target tables mentioned in the relational model:

- `staging.seccion_geo`
- `staging.fact_genero_edad`
- `staging.fact_genero_pais`
- `staging.candidatura_raw`
- `staging.datos_mesa_raw`
- `staging.resultados_mesa_raw`
- `staging.resultados_municipio_raw`
- `staging.encuesta_<nombre>`

Catastro GML loading:

- `etl/catastro/load_cp_gml_to_postgis.py` loads cadastral parcels into `staging.catastro_cp_raw`.
- `etl/catastro/load_bu_gml_to_postgis.py` loads building parts into `staging.catastro_bu_raw`.
- Geometries are transformed to EPSG:4326.
- `source_file` is added for traceability.

`staging.catastro_cp_raw` columns:

- `gml_id`
- `areaValue`
- `areaValue_uom`
- `beginLifespanVersion`
- `endLifespanVersion`
- `localId`
- `namespace`
- `label`
- `nationalCadastralReference`
- `pos`
- `geometry`
- `source_file`

`staging.catastro_bu_raw` columns:

- `gml_id`
- `beginLifespanVersion`
- `conditionOfConstruction`
- `localId`
- `namespace`
- `horizontalGeometryEstimatedAccuracy`
- `horizontalGeometryEstimatedAccuracy_uom`
- `horizontalGeometryReference`
- `referenceGeometry`
- `numberOfFloorsAboveGround`
- `heightBelowGround`
- `heightBelowGround_uom`
- `numberOfFloorsBelowGround`
- `geometry`
- `source_file`

`staging.catastro_cp_mijas` adds section assignment:

- `seccion_id`
- `cod_provincia`
- `cod_municipio`
- `cod_distrito`
- `cod_seccion`
- raw parcel fields and geometry

`staging.catastro_bu_mijas` adds section assignment:

- `seccion_id`
- `cod_provincia`
- `cod_municipio`
- `cod_distrito`
- `cod_seccion`
- raw building-part fields and geometry

### core

Canonical relational domain model.

Main dimensions:

- `core.municipio`
- `core.seccion`
- `core.mesa`
- `core.election_type`
- `core.election`
- `core.candidatura`

Main facts:

- `core.poblacion_edad`
- `core.poblacion_nacimiento`
- `core.datos_mesa`
- `core.resultados_mesa`
- `core.resultados_municipio`

Future tables mentioned in the relational model:

- `core.indicadores_socioeconomicos`
- `core.encuesta_respuesta`
- `core.encuesta_agregada_seccion`

Main geography:

`core.seccion`:

- `cod_provincia`
- `cod_municipio`
- `cod_distrito`
- `cod_seccion`
- `geom`

Demography:

`core.poblacion_edad`:

- primary key: `seccion_id`, `anio`, `genero`, `edad_cohorte`
- `seccion_id`
- `anio`
- `genero`
- `edad_cohorte`
- `poblacion`

Income:

`core.renta_seccion`:

- primary key: `seccion_id`, `anio`
- `seccion_id`
- `anio`
- `renta_media_persona`
- `renta_media_hogar`
- `fuente`
- `updated_at`

Socioeconomic Intelligence:

`core.socioeconomic_indicator_section` is the canonical long table for historical socioeconomic indicators by section.

- primary key: `seccion_id`, `anio`, `domain`, `indicator_code`, `category_code`
- `domain` groups the source family: `education_level`, `occupation_status`, `occupation_activity`, `activity_branch`, `professional_status`, `income_inequality`, `income_source`
- `value_type` makes scale explicit: `count`, `percentage`, `ratio`, `index`
- `unit` uses stable analytical units: `persons`, `percent`, `ratio`, `index`
- raw source labels are preserved in `indicator_label` and `category_label`
- source traceability is preserved in `source_file` and `fuente`

`core.socioeconomic_indicator_catalog` documents each canonical indicator/category used by the long table.

Important modeling notes:

- INE files with a `Sexo` column are loaded into the canonical layer using `Sexo = Total`; raw keeps the original male/female rows for future disaggregation.
- Education data currently exposes `Educación primaria e inferior` as one combined category. It should not be treated as separate `Sin estudios` and `Primarios` unless a more detailed source is added.
- Count-based categories are stored as counts in core. Percentages such as `pct_higher_studies` are derived in marts using the source total category.
- Income-source values are stored as 0-100 percentages.
- Synthetic socioeconomic scores are future comparative signals, not absolute truths, and need explicit methodology before production use.

Electoral:

`core.election`:

- `election_id`
- `tipo_eleccion_code`
- `anio`
- `mes`
- `num_vuelta`
- `election_date`

`core.candidatura`:

- `election_id`
- `cod_candidatura`
- `siglas`
- `denominacion`

`core.datos_mesa`:

- mesa-level census and voting totals.

`core.resultados_mesa`:

- mesa-level candidate votes.

### marts

Analytical layer for maps, dashboards, APIs and model features.

Target marts mentioned in the relational model:

- `marts.demografia_seccion_anio`
- `marts.electoral_seccion_anio`
- `marts.features_panel`
- `marts.mapa_seccion_anio`
- `marts.encuesta_seccion_anio`

Current project marts and analytical views:

- `marts.dim_seccion_display`
- `marts.v_geografia_seccion`
- `marts.v_mapa_seccion_2023`
- `marts.v_poblacion_seccion_anio`
- `marts.v_resultados_seccion_anio`
- `marts.v_income_level`
- `marts.v_socioeconomic_indicators`
- `marts.v_socioeconomic_profile`
- `marts.v_socioeconomic_intelligence_base`
- `marts.socioeconomic_intelligence_signals`
- `marts.ml_socioeconomic_section_panel`
- `marts.mijas_features_panel`

## Socioeconomic Intelligence

Sources currently integrated from `data/raw/ine`:

- `29070_Mijas_NivelEstudios_2021_2024.csv`
- `29070_Mijas_Ocupacion_2021_2024.csv`
- `29070_Mijas_Actividad_2021_2023.csv`
- `29070_Mijas_RamaActividad_2021_2023.csv`
- `29070_Mijas_SitProfesional_2021_2023.csv`
- `29070_Mijas_IndiceGini_DistribucionRenta_2015_2023.csv`
- `29070_Mijas_FuenteIngresos_2019_2023.csv`

ETL entrypoint:

- `etl/economic/load_socioeconomic_indicators.py`

SQL assets:

- raw DDL: `sql/raw/007_create_raw_ine_socioeconomic.sql`
- staging DDL: `sql/staging/008_create_staging_socioeconomic_indicator_section.sql`
- core DDL: `sql/core/008_create_core_socioeconomic_indicators.sql`
- marts DDL: `sql/marts/020_socioeconomic_intelligence.sql`
- QA: `sql/qa/socioeconomic_intelligence_qa.sql`

Marts:

- `marts.v_socioeconomic_indicators`: long analytical view enriched with geometry/display fields, quintile and 0-100 normalized index.
- `marts.v_socioeconomic_profile`: one row per `seccion_id + anio`, with pivoted socioeconomic variables.
- `marts.v_socioeconomic_intelligence_base`: profile joined to income level, population and average age where available.
- `marts.socioeconomic_intelligence_signals`: premium section-year mart for Human Capital, Vulnerability, Resilience, Productive Complexity and Inequality Pressure. Scores are 0-100 comparative territorial signals normalized within municipality/year and expose completeness percentages.
- `marts.ml_socioeconomic_section_panel`: ML-ready section-year panel prepared from `marts.socioeconomic_intelligence_signals`.

Methodology:

- See `docs/metrics/socioeconomic_intelligence_methodology.md`.
- Synthetic socioeconomic scores are comparative territorial signals, not causal claims or absolute measures.
- Missing inputs are handled through proportional reweighting and score-specific completeness fields.
- `marts.v_mapa_age_structure_2023`
- `marts.mv_electoral_behavior`
- `marts.real_estate_section_profile_base`
- `marts.real_estate_built_section_2023`
- `marts.territorial_intelligence_section_2023`

## Main Marts

### `marts.dim_seccion_display`

Display dimension:

- `seccion_id`
- `seccion_numero_visible`
- `nombre_barrio`
- `zona_macro`
- `label_cliente`

### `marts.v_geografia_seccion`

Geography view:

- `seccion_id`
- `area_m2`
- `area_km2`

### `marts.v_mapa_seccion_2023`

Map-facing section view:

- `seccion_id`
- `seccion_numero_visible`
- `nombre_barrio`
- `zona_macro`
- `label_cliente`
- `geom`
- `geom_json`

### `marts.v_poblacion_seccion_anio`

Section-year population view:

- `seccion_id`
- `anio`
- `pob_total`
- `pob_h`
- `pob_m`
- `pct_h`
- `pct_m`
- `pob_0_19`
- `pob_0_14`
- `pob_15_29`
- `pob_30_44`
- `pob_45_64`
- `pob_65p`
- `pct_0_14`
- `pct_15_29`
- `pct_30_44`
- `pct_45_64`
- `pct_65p`
- `dependency_ratio`

### `marts.v_resultados_seccion_anio`

Section-year electoral results view:

- `seccion_id`
- `anio`
- `election_id`
- `censo`
- `votos_emitidos`
- `votos_validos`
- `votos_blanco`
- `votos_nulos`
- `participacion`
- `blanco_pct`
- `nulos_pct`
- `cod_candidatura_ganadora`
- `sigla_ganadora`
- `votos_ganador`
- `votos_pp`
- `votos_psoe`
- `votos_vox`
- `pct_pp`
- `pct_psoe`
- `pct_vox`

### `marts.v_income_level`

Income classification view:

- `seccion_id`
- `anio`
- `renta_media_persona`
- `renta_media_hogar`
- `income_quintile`
- `income_level`
- `income_rank_municipal`
- `income_index`

### `marts.mijas_features_panel`

Primary feature panel:

- materialized view.
- one row per section/year.
- joins geography, demography, electoral results and income.

Key columns:

- `seccion_id`
- `anio`
- `election_id`
- `area_m2`
- `area_km2`
- `densidad`
- population fields
- electoral participation and party fields
- income fields
- `ratio_censo_poblacion`
- `ratio_votantes_poblacion`

### `marts.v_mapa_age_structure_2023`

Age structure map view:

- `seccion_id`
- display fields
- `geom`
- `anio`
- `average_age`
- `age_group`
- `age_group_label`
- `age_color_key`
- `total_poblacion`
- `over_65_pct`
- `under_30_pct`
- `densidad`
- `density_level`

### `marts.mv_electoral_behavior`

Electoral behavior materialized view:

- `seccion_id`
- `anio`
- `election_id`
- `geom`
- `geojson`
- `winning_party`
- `winning_party_pct`
- `runner_up_party`
- `runner_up_pct`
- `victory_margin_pct`
- `local_vote_pct`
- `national_vote_pct`
- `left_bloc_pct`
- `right_bloc_pct`
- `fragmentation_index`
- `competitive_parties_count`
- `vote_concentration_index`
- `localism_index`
- `localism_category`
- `party_results_json`
- party vote percentages and votes

### `marts.real_estate_section_profile_base`

Real-estate parcel profile base:

- `seccion_id`
- `num_parcelas`
- `superficie_total_parcelas_m2`
- `superficie_media_parcela_m2`
- `densidad_parcelaria`

### `marts.real_estate_built_section_2023`

Built footprint section profile:

- `seccion_id`
- `num_building_parts`
- `huella_construida_m2`
- `huella_media_building_part_m2`

### `marts.territorial_intelligence_section_2023`

Territorial intelligence materialized view:

- one row per Mijas section for 2023.
- not a formal property valuation.
- combines market references, Catastro parcel/building structure, density, income, age and participation.

Key fields:

- `seccion_id`
- `anio`
- display fields
- `geom`
- `pob_total`
- `densidad`
- `renta_media_persona`
- `renta_media_hogar`
- `edad_media`
- `participacion`
- `num_parcelas`
- `superficie_total_parcelas_m2`
- `superficie_media_parcela_m2`
- `num_building_parts`
- `huella_construida_m2`
- `huella_media_building_part_m2`
- `indice_construido`
- `precio_m2_observado`
- `precio_m2_municipal_baseline`
- `valor_catastral_distrito_baseline`
- `market_reference_m2`
- `price_reference_is_observed`
- `market_reference_confidence_weight`
- `price_norm`
- `income_norm`
- `density_norm`
- `footprint_norm`
- `market_pressure_index`
- `opportunity_signal_score`
- `residential_saturation_index`
- `urban_prestige_signal`
- `foreign_demand_exposure`
- `territorial_signal_score`
- `market_pressure_label`
- `opportunity_label`
- `residential_profile_label`
- `prestige_label`
- `territorial_signal_label`
- `confidence_level`
- `market_reference_type`
- `calibration_source`

## API Shape

Geo endpoint:

- Uses `backend/app/db/sql/geo_sections.sql`.
- Returns GeoJSON `FeatureCollection`.
- Properties include section identity, display fields, population, density, income, electoral behavior, age structure and real-estate / territorial intelligence scores.

Section detail endpoint:

- Uses `backend/app/db/sql/section_detail.sql`.
- Returns semantic blocks:
  - `display`
  - `geography`
  - `demography`
  - `electoral`
  - `income`

Backend Pydantic schema references:

- `backend/app/schemas/geo.py`
- `backend/app/schemas/section.py`

## Modeling Notes

Use `seccion_id` as the stable join key across layers.

Use `marts.mijas_features_panel` for general section-level feature engineering.

Use `marts.territorial_intelligence_section_2023` for real-estate/territorial strategy prompts, but describe it as a comparative strategic signal layer, not as an appraisal or exact market-price model.

Use `marts.v_mapa_seccion_2023` when geometry/display labels are needed.

Percent columns are usually stored as ratios from 0 to 1 unless explicitly labeled or normalized as 0 to 100 scores.

Territorial scores are 0-100 comparative indexes, not absolute truths.

## Data Quality Rules

- `seccion_id` must always exist in `core.seccion`.
- analytical marts should preserve exactly 37 rows for Mijas 2023 unless explicitly documented.
- geometry joins should use LEFT JOIN carefully to avoid row multiplication.
- ratios and percentages should avoid divide-by-zero using `NULLIF`.
- analytical views should avoid duplicate rows per `seccion_id + anio`.
- all map-facing marts should expose geometry in EPSG:4326.
- QA queries should check row counts, nulls, duplicate keys and geometry validity.
- materialized views should document refresh requirements.

## Frontend Semantic Rules

Dashboard layers are mutually exclusive:

- population
- ageStructure
- electoralBehavior
- incomeLevel
- territorialIntelligence

Tooltips:

- mouseover tooltip = detailed transient inspection.
- right panel = summarized interpretation.

Map coloring:

- one dominant semantic dimension per layer.
- avoid mixing unrelated scales/colors in the same layer.
- legends must reflect the active layer only.
- frontend labels should come from display dimensions or mart aliases, not from raw IDs when avoidable.

## Strategic Positioning

SocTrace is not:

- a GIS viewer.
- a raw BI dashboard.
- a property appraisal tool.

SocTrace is:

- a territorial intelligence platform.
- a comparative spatial analytics platform.
- a strategic decision-support system.

Territorial Intelligence and real-estate-related outputs must be described as comparative strategic signals, not as formal valuations or appraisals.

## Future-Proof Modeling

New marts should:

- support multi-year expansion.
- avoid hardcoded 2023 assumptions internally.
- preserve stable `seccion_id`.
- prefer long/tidy analytical structures over wide hardcoded columns when future categories may change.
- expose frontend-friendly labels separately from canonical IDs.
- keep geometry, display labels and analytical metrics clearly separated.
- document whether percentage fields are 0-1 ratios or 0-100 values.
- be designed so that new municipalities can be added later without rewriting core logic.

## Known Documentation and Database Divergence

Some objects exist in the live database but are not fully represented as checked-in SQL DDL files in the repo.

Live DB objects observed that are only partially represented in repo SQL include:

- `staging.catastro_cp_mijas`
- `staging.catastro_bu_mijas`
- `staging.catastro_valor_distrito_mijas`
- `staging.catastro_valor_distrito_mijas_2023`
- `staging.catastro_valor_seccion_ajustado`
- `staging.catastro_valor_seccion_base_2023`
- `staging.factor_construido_seccion`
- `staging.vivienda_valor_tasado_mijas_2023`
- `staging.vivienda_valor_tasado_municipio_raw`
- `marts.real_estate_section_profile_base`
- `marts.real_estate_built_section_2023`
- `marts.real_estate_section_premium_2023`
- `marts.real_estate_section_premium_2023_v2`
- `marts.real_estate_section_premium_2023_v3`
- `marts.territorial_intelligence_section_2023`

Note: the checked-in SQL and the live DB are not perfectly identical. The live DB currently contains additional real-estate marts and Catastro staging tables that are not fully represented as SQL DDL files in the repo.
