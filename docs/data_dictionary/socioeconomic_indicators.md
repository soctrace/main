# Socioeconomic Indicators Data Dictionary

Canonical table: `core.socioeconomic_indicator_section`

Catalog table: `core.socioeconomic_indicator_catalog`

Grain: one row per `seccion_id + anio + domain + indicator_code + category_code`.

## Domains

| domain | indicator_code | years | value_type | unit | source |
|---|---|---:|---|---|---|
| `education_level` | `education_level` | 2021-2024 | `count` | `persons` | `29070_Mijas_NivelEstudios_2021_2024.csv` |
| `occupation_status` | `occupation_status` | 2021-2024 | `count` | `persons` | `29070_Mijas_Ocupacion_2021_2024.csv` |
| `occupation_activity` | `occupation_activity` | 2021-2023 | `count` | `persons` | `29070_Mijas_Actividad_2021_2023.csv` |
| `activity_branch` | `activity_branch` | 2021-2023 | `count` | `persons` | `29070_Mijas_RamaActividad_2021_2023.csv` |
| `professional_status` | `professional_status` | 2021-2023 | `count` | `persons` | `29070_Mijas_SitProfesional_2021_2023.csv` |
| `income_inequality` | `income_inequality` | 2015-2023 | `index` / `ratio` | `index` / `ratio` | `29070_Mijas_IndiceGini_DistribucionRenta_2015_2023.csv` |
| `income_source` | `income_source` | 2019-2023 | `percentage` | `percent` | `29070_Mijas_FuenteIngresos_2019_2023.csv` |

## Categories

### education_level

| category_code | label | note |
|---|---|---|
| `total` | Total | denominator for percentage marts |
| `primary_or_below` | Educación primaria e inferior | INE combines primary and below; do not split into no studies/primary without a more detailed source |
| `lower_secondary` | Primera etapa de Educación Secundaria y similar | derived as percentage in marts |
| `upper_secondary` | Segunda etapa de Educación Secundaria y Educación Postsecundaria no Superior | derived as percentage in marts |
| `higher` | Educación superior | exposed as `pct_higher_studies` |

### occupation_status

| category_code | label |
|---|---|
| `total` | Total |
| `employed` | Ocupado/a |
| `unemployed` | Parado/a |
| `student` | Estudiante |
| `pensioner` | Perceptor/a pensión de incapacidad, jubilación, prejubilación |
| `other_inactive` | Otra situación de inactividad |

### occupation_activity

| category_code | label |
|---|---|
| `total` | Total |
| `directors_managers_professionals` | Directores/gerentes y profesionales/técnicos de nivel medio o alto |
| `skilled_workers` | Trabajadores cualificados y oficiales/operarios de nivel bajo |
| `elementary_occupations` | Ocupaciones elementales |
| `unknown` | No consta |

### activity_branch

| category_code | label |
|---|---|
| `total` | Total CNAE |
| `agriculture` | Agricultura, ganadería y pesca |
| `industry` | Industria |
| `construction` | Construcción |
| `services` | Servicios |
| `unknown` | No consta |

### professional_status

| category_code | label |
|---|---|
| `total` | Total |
| `self_employed` | Trabajador por cuenta propia |
| `employee_or_other` | Trabajador por cuenta ajena y otra situación |

### income_inequality

| category_code | label | value_type | unit |
|---|---|---|---|
| `gini_index` | Índice de Gini | `index` | `index` |
| `p80_p20_ratio` | Distribución de la renta P80/P20 | `ratio` | `ratio` |

### income_source

| category_code | label | value_type | unit |
|---|---|---|---|
| `salary` | Fuente de ingreso: salario | `percentage` | `percent` |
| `pension` | Fuente de ingreso: pensiones | `percentage` | `percent` |
| `unemployment_benefits` | Fuente de ingreso: prestaciones por desempleo | `percentage` | `percent` |
| `social_benefits` | Fuente de ingreso: otras prestaciones | `percentage` | `percent` |
| `other_income` | Fuente de ingreso: otros ingresos | `percentage` | `percent` |

## Future Synthetic Signals

Potential future scores:

- `socioeconomic_status_index`
- `education_capital_index`
- `labor_market_strength_index`
- `pension_dependency_index`
- `inequality_pressure_index`
- `welfare_dependency_index`
- `service_economy_index`
- `entrepreneurial_signal_index`
- `socioeconomic_vulnerability_index`

These scores should be treated as comparative signals. They are not absolute truths and need documented methodology, weighting and validation before dashboard or ML use.
