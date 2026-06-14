# SocTrace - Data Model

## Canonical Geographic Key

seccion_id

Examples:
2907001001

Future normalized variants:
- province
- municipality
- district
- section

---

## Main Tables

## core.seccion

Geographic polygons by census/electoral section.

Fields:
- seccion_id
- geometry
- municipality metadata

---

## core.poblacion_edad

Population by:

- seccion_id
- anio
- genero
- edad_cohorte

Measures:
- poblacion

---

## core.resultados_mesa

Election results by mesa.

Fields:
- election_id
- seccion_id
- candidatura
- votos

---

## core.candidatura

Party dictionary.

---

## Main Analytical Views

## marts.v_poblacion_seccion_anio

Aggregated section demographics.

Includes:

- pob_total
- age groups
- percentages
- dependency ratio

---

## marts.v_resultados_seccion_anio

Aggregated electoral results by section/year.

Includes:

- censo
- participacion
- winning party
- vote shares

---

## marts.mijas_features_panel

Primary ML / analytics dataset.

Grain:
1 row = section + year

Contains:
- demographics
- density
- electoral shares
- participation
- geo indicators

---

## Future Temporal Model

Primary grain:

seccion_id + anio

Years planned:
- 2023
- 2019
- 2015

---

## Naming Rules

snake_case only

Examples:
- pob_total
- pct_psoe
- zona_macro