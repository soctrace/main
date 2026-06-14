\echo 'QA electoral forecasting 2027'

SELECT COUNT(*) AS forecast_sections
FROM marts.electoral_forecasting_features_2027;

SELECT
    COUNT(*) FILTER (WHERE forecast_confidence NOT BETWEEN 0 AND 100) AS invalid_confidence,
    COUNT(*) FILTER (WHERE volatility NOT BETWEEN 0 AND 100) AS invalid_volatility,
    COUNT(*) FILTER (WHERE abstention_risk NOT BETWEEN 0 AND 100) AS invalid_abstention_risk,
    COUNT(*) FILTER (WHERE swing_sections NOT BETWEEN 0 AND 100) AS invalid_swing_sections,
    COUNT(*) FILTER (WHERE model_version <> 'electoral_structural_baseline_2027_v1') AS invalid_model_version
FROM marts.electoral_forecasting_features_2027;

SELECT *
FROM marts.electoral_forecasting_municipality_2027
ORDER BY municipality_id;
