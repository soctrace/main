# Semantic Layer v2

## Purpose

Semantic Layer v2 is the deterministic translation layer between human questions and reusable analytical operations for the Municipal Intelligence Agent. It maps Spanish from Spain, selected English synonyms, metrics, entities, operations, filters, years, parties and response hints onto the canonical `marts.agent_*` data contract.

It is not an OpenAI planner and it is not a list of one-off questions.

## Metric Definitions

Metrics live in `backend/app/ask/semantic_catalog.yaml` under `metrics`. Each supported metric defines:

- `label`
- `description`
- `view`
- `field`
- `entity`
- `type`
- `default_operation`
- `default_order`
- `synonyms_es`
- `synonyms_en`
- `supported_operations`
- `caveats`

All supported metrics must point only to:

- `marts.agent_section_profile`
- `marts.agent_population_age`
- `marts.agent_electoral_results`
- `marts.agent_electoral_summary`
- `marts.agent_income_sources`
- `marts.agent_housing_profile`
- `marts.agent_section_lookup`

## Operation Selection

The interpreter applies layered logic:

1. Deterministic phrase patterns for known high-value questions.
2. Synonym matching to select metrics.
3. Question-form routing to select operations.
4. Explicit pending/unsupported reasons when a concept is known but not executable.

Examples:

- `sección más joven` -> `rank_sections` + `average_age` + `asc`
- `concentran más jubilados` -> `rank_sections` + `population_over_65` + `desc`
- `ha rejuvenecido desde 2021` -> `compare_years` + `average_age` + `largest_decrease`
- `gana siempre el PP` -> `persistent_winner` + `winner_party` + `party=PP`

## Supported Metrics

Population and age:

- `population_total`
- `population_density`
- `population_under_18`
- `population_under_30`
- `population_over_65`
- `population_under_18_pct`
- `population_under_30_pct`
- `population_over_65_pct`
- `average_age`

Income:

- `income_individual`
- `income_household`
- `salary_share`
- `pension_share`
- `unemployment_share`

Electoral:

- `vote_pct`
- `winner_party`
- `participation_pct`
- `abstention_pct`
- `winner_vote_pct`
- `margin_pct`

Housing and urban:

- `market_price_estimated_m2`
- `estimated_cadastral_value_m2`
- `market_to_cadastral_ratio`
- `residential_pressure_index`
- `building_intensity`
- `parcel_density`
- `built_footprint`
- `avg_plot_size`

## Supported Operations

- `rank_sections`
- `aggregate_municipality`
- `compare_years`
- `party_strength`
- `persistent_winner`
- `historical_party_average`
- `age_cohort_projection`
- `population_growth`
- `cross_metric_ranking` as beta scoring
- `correlation_analysis` as beta section-level correlation

Cataloged for future use but not exposed as fully supported MVP operations:

- `filter_sections`
- `section_profile`

## Pending Operations

- Clustering and similarity search.
- Broad automatic variable search for strongest correlations.
- Predictive modeling beyond deterministic cohort projection.
- Planner-level multi-step reasoning.

## Adding A Metric

1. Add the metric to `semantic_catalog.yaml`.
2. Point `view` to one approved `marts.agent_*` relation.
3. Set `field` to an existing column in that view.
4. Add Spanish and English synonym lists.
5. Add supported operations.
6. Run `python scripts/validate_semantic_layer_v2.py` from `backend`.
7. Add a focused test in `backend/tests/ask/test_semantic_layer_v2.py`.

## Adding A Synonym

Add the phrase to `synonyms_es` or `synonyms_en`. Prefer specific phrases over broad words. For example, use `poblacion menor de 30 anos` so it wins over generic `mas poblacion`.

## Adding A Municipality

The semantic layer accepts `municipality_id` and does not hardcode Mijas in generated SQL. A future municipality must have rows in the same canonical `agent_*` views with the same fields. Section labels should be present in the agent views or lookup table.

## Examples

`¿Cuál es la sección con mayor población?`

- operation: `rank_sections`
- metric: `population_total`
- order: `desc`
- limit: `1`

`¿Qué secciones concentran más jubilados?`

- operation: `rank_sections`
- metric: `population_over_65`
- caveat: age proxy, not pension status

`¿Qué sección ha rejuvenecido más desde 2021?`

- operation: `compare_years`
- metric: `average_age`
- direction: `largest_decrease`
- start_year: `2021`

`¿Qué secciones combinan renta baja y alta abstención?`

- operation: `cross_metric_ranking`
- metrics: `income_individual`, `abstention_pct`
- status: beta
