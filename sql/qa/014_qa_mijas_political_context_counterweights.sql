\echo 'QA Mijas political context and electoral counterweights 2027'

SELECT COUNT(*) AS contextual_priors
FROM core.mijas_contextual_priors;

SELECT COUNT(*) AS section_context_rows
FROM core.mijas_section_context;

SELECT COUNT(*) AS mapped_forecast_sections
FROM marts.electoral_forecast_counterweights_2027;

SELECT d.seccion_id
FROM marts.dim_seccion_display d
LEFT JOIN core.mijas_section_context c
  ON c.seccion_id = d.seccion_id
WHERE c.territorial_cluster IS NULL
ORDER BY d.seccion_id;

SELECT
    COUNT(*) FILTER (WHERE contextual_vote_adjustment_pct NOT BETWEEN -4 AND 4) AS invalid_vote_adjustments,
    COUNT(*) FILTER (WHERE contextual_uncertainty NOT BETWEEN 0 AND 100) AS invalid_uncertainty,
    COUNT(*) FILTER (WHERE contextual_confidence IS NULL) AS missing_contextual_confidence,
    COUNT(*) FILTER (WHERE conservative_localist_split_is_active) AS active_unconfirmed_split_risks
FROM marts.electoral_forecast_counterweights_2027;

SELECT
    COUNT(*) FILTER (WHERE forecast_confidence IS NULL) AS missing_forecast_confidence,
    ROUND(AVG(structural_forecast_confidence), 2) AS average_structural_confidence,
    ROUND(AVG(forecast_confidence), 2) AS average_final_confidence,
    ROUND(AVG(projected_vote_share - structural_projected_vote_share), 2) AS average_leader_share_delta
FROM marts.electoral_forecasting_features_2027;

SELECT
    seccion_id,
    contextual_adjustment_score,
    contextual_vote_adjustment_pct,
    contextual_confidence
FROM marts.electoral_forecast_counterweights_2027
ORDER BY ABS(contextual_adjustment_score) DESC, seccion_id
LIMIT 10;

SELECT
    seccion_id,
    contextual_uncertainty,
    cs_orphan_vote_pool,
    pmp_localist_transfer_pool,
    contextual_confidence
FROM marts.electoral_forecast_counterweights_2027
ORDER BY contextual_uncertainty DESC, seccion_id
LIMIT 10;
