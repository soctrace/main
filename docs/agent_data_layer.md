# Agent Data Layer SocTrace

Fecha: 2026-06-08  
Script principal: `sql/marts/030_agent_data_layer.sql`

Esta capa crea vistas canónicas `marts.agent_*` para que el futuro Municipal Intelligence Agent consulte datos estables sin depender de vistas `ask_*` incompletas o no aplicadas en la base viva. Para rendimiento, `marts.agent_section_profile` se expone como vista sobre una base materializada interna (`marts.agent_section_profile_base`), evitando que las lecturas principales del agente excedan el timeout operativo.

## Principios

- Nombres técnicos consistentes en inglés.
- Identidad territorial común: `municipio_id`, `municipio_nombre`, `section_id`, `section_name`.
- Estructura multi-municipio mediante prefijo INE de `section_id`.
- Actualmente la cobertura principal está poblada para Mijas (`29070`).
- No se inventan valores: si una fuente no contiene un indicador para un año, queda `NULL`.
- Se separan dominios temporales para evitar mezclar indebidamente población, renta, elecciones y vivienda.

## `marts.agent_section_lookup`

| Campo | Descripción |
|---|---|
| `municipio_id` | Código municipal derivado de `section_id`. |
| `municipio_nombre` | Nombre municipal conocido; Mijas para `29070`. |
| `section_id` | Identificador de sección censal. |
| `section_number` | Número visible de sección. |
| `section_name` | Nombre legible para usuario. |
| `display_name` | Alias legible equivalente. |

Grano: una fila por sección.  
Fuente: `marts.dim_seccion_display`.  
Cobertura actual: Mijas, 37 secciones actuales.  
Limitaciones: depende de la tabla de display; secciones históricas que no estén en esa tabla pueden no aparecer.

Ejemplo:

```sql
SELECT *
FROM marts.agent_section_lookup
WHERE municipio_id = '29070'
ORDER BY section_number;
```

## `marts.agent_population_age`

| Campo | Descripción |
|---|---|
| `municipio_id`, `municipio_nombre` | Municipio. |
| `section_id`, `section_name` | Sección. |
| `year` | Año de población. |
| `gender` | `H`, `M` o `all` si la fuente viniera agregada. |
| `age_cohort` | Cohorte original. |
| `age_min`, `age_max` | Rango de edad parseado. |
| `people` | Personas en la cohorte/género. |

Grano: municipio + sección + año + género + cohorte.  
Fuente: `core.poblacion_edad`.  
Cobertura actual: Mijas, años 2021-2025 según fuente viva.  
Limitaciones: la edad viene en cohortes quinquenales; rangos que cortan cohortes requieren prorrateo.

Ejemplo:

```sql
SELECT section_name, SUM(people) AS people_15_19
FROM marts.agent_population_age
WHERE municipio_id = '29070'
  AND year = 2025
  AND age_cohort = '15-19'
GROUP BY section_name
ORDER BY people_15_19 DESC;
```

## `marts.agent_electoral_results`

| Campo | Descripción |
|---|---|
| `municipio_id`, `municipio_nombre` | Municipio. |
| `section_id`, `section_name` | Sección. |
| `election_id`, `election_type`, `election_year`, `election_month`, `election_label` | Identidad electoral. |
| `party` | Siglas/partido original. |
| `canonical_party` | Familia canónica normalizada. |
| `votes`, `valid_votes`, `vote_pct` | Resultado electoral por partido. |

Grano: sección + elección + partido.  
Fuentes: `marts.v_resultados_seccion_eleccion`, `marts.agent_section_lookup`.  
Cobertura actual: elecciones normalizadas cargadas para Mijas.  
Limitaciones: la normalización canónica depende de `core.candidatura_alias` y reglas adicionales para locales/otros.

Ejemplo:

```sql
SELECT section_name, canonical_party, vote_pct
FROM marts.agent_electoral_results
WHERE municipio_id = '29070'
  AND election_type = 'MUNICIPALES'
  AND election_year = 2023
ORDER BY vote_pct DESC
LIMIT 10;
```

## `marts.agent_electoral_summary`

| Campo | Descripción |
|---|---|
| `municipio_id`, `municipio_nombre` | Municipio. |
| `section_id`, `section_name` | Sección. |
| `election_id`, `election_type`, `election_year`, `election_label` | Elección. |
| `census`, `valid_votes`, `total_votes` | Magnitudes electorales. |
| `participation_pct`, `abstention_pct` | Participación y abstención. |
| `winner_party`, `winner_vote_pct` | Primera fuerza. |
| `second_party`, `second_vote_pct` | Segunda fuerza. |
| `margin_pct` | Diferencia entre primera y segunda fuerza. |

Grano: sección + elección.  
Fuentes: `marts.agent_electoral_results`, `marts.mv_electoral_behavior`.  
Limitaciones: ganador y segundo se derivan de porcentajes normalizados; si faltan partidos en una elección, el margen puede estar incompleto.

Ejemplo:

```sql
SELECT section_name, winner_party, second_party, margin_pct
FROM marts.agent_electoral_summary
WHERE municipio_id = '29070'
  AND election_type = 'MUNICIPALES'
  AND election_year = 2023
ORDER BY margin_pct ASC;
```

## `marts.agent_income_sources`

| Campo | Descripción |
|---|---|
| `municipio_id`, `municipio_nombre` | Municipio. |
| `section_id`, `section_name` | Sección. |
| `year` | Año. |
| `income_individual`, `income_household` | Renta media individual y por hogar. |
| `salary_share`, `pension_share`, `unemployment_share`, `other_income_share` | Peso de fuentes de ingresos. |

Grano: sección + año.  
Fuentes: `marts.v_income_level_layer`, `marts.v_income_sources_profile`.  
Cobertura actual: Mijas, renta y fuentes INE 2019-2023 según disponibilidad.  
Limitaciones: `other_income_share` suma otros ingresos y otras prestaciones; las fuentes son porcentajes por sección.

Ejemplo:

```sql
SELECT section_name, year, income_individual, pension_share
FROM marts.agent_income_sources
WHERE municipio_id = '29070'
  AND year = 2023
ORDER BY pension_share DESC;
```

## `marts.agent_housing_profile`

| Campo | Descripción |
|---|---|
| `municipio_id`, `municipio_nombre` | Municipio. |
| `section_id`, `section_name` | Sección. |
| `year` | Año, actualmente 2023. |
| `parcel_density`, `built_footprint`, `avg_plot_size`, `building_intensity` | Entorno construido. |
| `estimated_cadastral_value_m2`, `market_price_estimated_m2`, `market_to_cadastral_ratio` | Valor inmobiliario estimado. |
| `housing_classification`, `residential_pressure_index` | Clasificación y presión residencial. |

Grano: sección + año.  
Fuentes: `marts.v_land_built_environment`, `marts.housing_intelligence_features_2023`, `marts.real_estate_section_premium_2023`.  
Cobertura actual: Mijas, 2023.  
Limitaciones: indicadores de mercado son estimaciones/proxies; no son tasación oficial ni predicción de precio.

Ejemplo:

```sql
SELECT section_name, market_price_estimated_m2, residential_pressure_index
FROM marts.agent_housing_profile
WHERE municipio_id = '29070'
ORDER BY market_price_estimated_m2 DESC;
```

## `marts.agent_section_profile`

| Campo | Descripción |
|---|---|
| Identidad | `municipio_id`, `municipio_nombre`, `section_id`, `section_name`, `year`. |
| Población | `population_total`, `population_density`, `average_age`. |
| Cohortes | `population_under_18`, `population_under_18_pct`, `population_under_30`, `population_under_30_pct`, `population_over_65`, `population_over_65_pct`. |
| Renta | `income_individual`, `income_household`. |
| Electoral | `participation_pct`, `abstention_pct`, `winner_party`. |
| Vivienda | `built_footprint`, `parcel_density`, `building_intensity`, `estimated_real_estate_value_m2`, `market_price_estimated_m2`, `housing_pressure_label`. |

Grano: sección + año de población.  
Tipo: vista canónica sobre `marts.agent_section_profile_base`, materialized view interna con índices por `municipio_id`, `section_id` y `year`.  
Fuentes: `marts.ask_population_profile`, `marts.agent_income_sources`, `marts.agent_electoral_summary`, `marts.agent_housing_profile`.  
Cobertura actual: Mijas, años de población 2021-2025; renta en años coincidentes disponibles; electoral usa última elección municipal disponible por sección; vivienda en 2023.  
Limitaciones: mezcla dominios con calendarios distintos; para análisis temporal fino usar las vistas de dominio separadas. Requiere `REFRESH MATERIALIZED VIEW marts.agent_section_profile_base` cuando cambien sus fuentes.

Ejemplo:

```sql
SELECT section_name, year, population_total, average_age, income_individual, abstention_pct
FROM marts.agent_section_profile
WHERE municipio_id = '29070'
  AND year = 2023
ORDER BY population_total DESC;
```
