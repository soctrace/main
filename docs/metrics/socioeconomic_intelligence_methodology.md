# Socioeconomic Intelligence Methodology

`marts.socioeconomic_intelligence_signals` exposes comparative territorial signals by `seccion_id + anio`.

These indices are not causal estimates, rankings of people, or absolute truths. They are normalized comparative signals within Mijas and within each year, designed for territorial analytics and dashboard exploration.

## Scale

Each score is expressed on a 0-100 scale:

- 0 = lower relative intensity within the municipality/year
- 100 = higher relative intensity within the municipality/year

Base variables are normalized by year using min-max normalization:

```sql
100 * (x - min_year) / NULLIF(max_year - min_year, 0)
```

For variables where lower values are better, the score uses:

```sql
100 - normalized_value
```

## Labels

All synthetic scores use the same label breaks:

- 0-20: Very Low
- 20-40: Low
- 40-60: Medium
- 60-80: High
- 80-100: Very High

## Missing Data

Scores are calculated with proportional reweighting. If an input variable is missing, its weight is removed from the denominator. Each score exposes a completeness field:

- `human_capital_completeness_pct`
- `vulnerability_completeness_pct`
- `resilience_completeness_pct`
- `productive_complexity_completeness_pct`
- `inequality_pressure_completeness_pct`

A low completeness score means the signal is weaker and should be interpreted cautiously.

## Human Capital

Purpose: educational capital, qualification and socioeconomic potential.

Weights:

- 35% `pct_higher_studies` normalized
- 25% qualified occupations normalized, using `pct_directors_managers_professionals`
- 20% `pct_employed` normalized
- 20% `renta_media_persona` normalized

## Vulnerability

Purpose: exposure to socioeconomic fragility.

Weights:

- 25% `pct_unemployed` normalized
- 25% low income pressure, inverse normalized `renta_media_persona`
- 20% low education, using `pct_primary_or_below` exposed as `pct_no_studies`
- 15% benefits dependency, strongest available signal from social or unemployment benefits
- 10% ageing pressure, normalized `over_65_pct`
- 5% inequality, normalized `gini_index`

## Resilience

Purpose: stability and capacity to absorb socioeconomic shocks.

Weights:

- 25% employment normalized
- 20% income normalized
- 20% income diversity entropy across income sources
- 15% lower inequality, inverse normalized Gini
- 10% higher education normalized
- 10% self-employment normalized

## Productive Complexity

Purpose: productive sophistication, occupational diversity and economic structure.

Weights:

- 30% qualified occupations normalized
- 25% sector diversity entropy across agriculture, industry, construction and services
- 20% business/professional activity proxy, currently `income_other` when detailed business income is unavailable
- 15% self-employment normalized
- 10% services plus industry weight normalized

## Inequality Pressure

Purpose: socioeconomic inequality and polarization pressure.

Weights:

- 40% normalized `gini_index`
- 35% normalized `p80_p20_ratio`
- 15% low income pressure
- 10% income polarization, derived from distance of `income_index` from the municipal midpoint

## Limitations

- `pct_no_studies` currently uses the available INE category `primary_or_below`; it should not be read as strictly "no studies".
- `pct_directors_managers` and `pct_technicians_professionals` are not separately available; the source combines directors, managers, professionals and technicians.
- `income_business_activity` and `income_real_estate` are currently unavailable in the source and remain `NULL`.
- Early years may have low completeness because education, occupation and activity sources start later than inequality data.
- These scores should be validated against domain expectations and local knowledge before being used in decision workflows.
