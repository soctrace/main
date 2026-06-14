# Electoral Forecast Counterweights 2027

## Purpose

`marts.electoral_forecast_counterweights_2027` adds bounded, auditable context to
the structural 2027 municipal forecast. It does not overwrite the structural
model.

## Data-Backed Counterweights

- PP brand reserve compares PP municipal support with approved regional and national election signals.
- PSOE local floor uses municipal stability and a bounded territorial prior for older Las Lagunas sections.
- Cs orphan vote pool measures observed decline and is not allocated mechanically.
- Por Mi Pueblo localist pool measures observed 2023 support and is not allocated mechanically.
- VOX national anchor summarizes approved non-municipal signals.
- Territorial cluster effect adds bounded sensitivity and uncertainty.

PP candidate reset potential is explicitly a contextual hypothesis derived from
the observed PP reserve. Conservative localist split risk is stored with
`is_active = false` until a human validates electoral supply.

## Output Contract

The forecast exposes:

- structural projected leader share;
- bounded contextual vote adjustment;
- final interpreted leader share;
- structural confidence;
- final confidence after contextual uncertainty;
- contextual drivers with evidence category.

The Campaign Builder note must read `Context-aware forecast` and explain that
priors are hypotheses, not facts.
