# SocTrace Local Analyst Platform

## Scope

The first production vertical is `SocTrace Local Analyst · Mijas`. The runtime
is municipality-agnostic: municipality knowledge lives in
`municipality_packs/<slug>/`, while approved analytical reads are restricted by
the backend allow-list in `backend/app/services/dataset_access.py`.

## Components

| Component | V1 implementation |
| --- | --- |
| Core agent boundary | Backend services consume approved marts and municipality packs only. External internet learning is outside the runtime contract. |
| Municipality pack | `municipality_packs/mijas/` with versioned, human-approved documents and structured contextual hypotheses. |
| Dataset access layer | `ApprovedDatasetAccess` rejects reads outside the explicit mart allow-list. |
| Forecast engine | `marts.electoral_forecasting_features_2027`, its narrow UI mart, municipal aggregate and `marts.electoral_forecast_counterweights_2027`. |
| Knowledge base | `MunicipalityPackService.load_municipality_context(slug)` loads retrievable versioned documents without hardcoding Mijas knowledge in application code. |
| Response generator | Forecast marts expose interpreted output, drivers and evidence categories. The UI renders the interpretation instead of raw model internals. |
| Confidence engine | Forecast confidence is computed from historical coverage, socioeconomic completeness, housing confidence and model stability. |
| Audit layer | Forecast service reads append question, datasets, variables, model and confidence to `core.agent_audit_log`. |
| Oraculum integration | Forecast marts expose reserved `oraculum_calibrated` and calibration-version fields. V1 keeps them inactive. |

## Forecast Contract

`electoral_structural_baseline_2027_v1` is an estimated scenario baseline with
bounded contextual counterweights. It is not polling, does not claim certainty
and does not use autonomous external sources. Its output must always distinguish
structural output, contextual hypothesis adjustment, final estimate and
confidence.

The model uses approved internal marts:

- `marts.mv_electoral_behavior`
- `marts.socioeconomic_intelligence_signals`
- `marts.housing_intelligence_features_2023`

The frontend consumes only the narrow forecast UI fields joined into the
section GeoJSON. Dedicated API endpoints expose interpreted municipality and
section outlooks for future analyst workflows.

## Loading The V1 Mart

```bash
psql -d mijas -v ON_ERROR_STOP=1 -f sql/marts/024_mijas_political_context_counterweights.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/marts/023_electoral_forecasting_2027.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/qa/013_qa_electoral_forecasting_2027.sql
psql -d mijas -v ON_ERROR_STOP=1 -f sql/qa/014_qa_mijas_political_context_counterweights.sql
```
