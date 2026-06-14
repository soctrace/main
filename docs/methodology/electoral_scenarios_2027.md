# Electoral Scenarios 2027

## Purpose

`marts.electoral_scenarios_2027` exposes four comparable municipal scenarios for
Mijas. They are auditable model interpretations, not closed predictions.

## Scenarios

- `structural`: current internally modeled baseline from historical electoral
  behavior, synthetic socioeconomic indicators and territorial features.
- `candidate_reset`: bounded test of PP local recovery after leadership renewal.
  It reduces the fixed weight of Cs and treats Cs and PMP as uncertain transfer
  pools rather than mechanically reallocating every vote.
- `localist_fragmentation`: conditional and more speculative test of a
  conservative localist supply fragmenting part of the center-right recovery.
  It does not assert a confirmed candidacy.
- `oraculum_ready`: preserves the baseline and identifies priority sections for
  future field validation. It contains no polling inputs and remains
  `oraculum_calibrated = false`.

## Electoral Supply Uncertainty

The mart exposes `cs_supply_uncertainty`, `pmp_supply_uncertainty`,
`localist_supply_uncertainty` and `candidate_supply_uncertainty`. These signals
affect confidence, contextual uncertainty and interpretation. They do not imply
that Cs, PMP or any hypothetical localist supply will disappear or stand in the
2027 election.

## Inputs And Traceability

All values derive from approved internal marts:

- `marts.electoral_forecasting_municipality_2027`
- `marts.electoral_forecasting_ui_2027`
- `marts.electoral_forecast_counterweights_2027`

The mart uses no external data and no autonomous polling calibration.
