-- QA for marts.territorial_intelligence_section_2023.
-- This layer is strategic territorial intelligence, not an individual appraisal.

SELECT COUNT(*) AS n_sections
FROM marts.territorial_intelligence_section_2023;

SELECT
    COUNT(*) FILTER (WHERE price_reference_is_observed) AS observed_price_sections,
    COUNT(*) FILTER (WHERE NOT price_reference_is_observed) AS fallback_price_sections,
    MIN(precio_m2_observado) AS min_observed_market_reference,
    MAX(precio_m2_observado) AS max_observed_market_reference
FROM marts.territorial_intelligence_section_2023;

SELECT seccion_id
FROM marts.territorial_intelligence_section_2023
WHERE precio_m2_observado IS NULL
ORDER BY seccion_id;

SELECT
    seccion_id,
    market_pressure_index,
    opportunity_signal_score,
    residential_saturation_index,
    urban_prestige_signal,
    foreign_demand_exposure,
    territorial_signal_score
FROM marts.territorial_intelligence_section_2023
WHERE market_pressure_index NOT BETWEEN 0 AND 100
   OR opportunity_signal_score NOT BETWEEN 0 AND 100
   OR residential_saturation_index NOT BETWEEN 0 AND 100
   OR urban_prestige_signal NOT BETWEEN 0 AND 100
   OR foreign_demand_exposure NOT BETWEEN 0 AND 100
   OR territorial_signal_score NOT BETWEEN 0 AND 100;

SELECT
    COUNT(*) FILTER (WHERE pob_total IS NULL) AS null_pob_total,
    COUNT(*) FILTER (WHERE densidad IS NULL) AS null_densidad,
    COUNT(*) FILTER (WHERE renta_media_persona IS NULL) AS null_renta_media_persona,
    COUNT(*) FILTER (WHERE num_parcelas IS NULL) AS null_num_parcelas,
    COUNT(*) FILTER (WHERE num_building_parts IS NULL) AS null_num_building_parts,
    COUNT(*) FILTER (WHERE market_reference_m2 IS NULL) AS null_market_reference
FROM marts.territorial_intelligence_section_2023;

SELECT 'territorial_signal_top' AS ranking, seccion_id, territorial_signal_score AS score, territorial_signal_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY territorial_signal_score DESC
LIMIT 5;

SELECT 'territorial_signal_bottom' AS ranking, seccion_id, territorial_signal_score AS score, territorial_signal_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY territorial_signal_score ASC
LIMIT 5;

SELECT 'market_pressure_top' AS ranking, seccion_id, market_pressure_index AS score, market_pressure_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY market_pressure_index DESC
LIMIT 5;

SELECT 'opportunity_top' AS ranking, seccion_id, opportunity_signal_score AS score, opportunity_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY opportunity_signal_score DESC
LIMIT 5;

SELECT 'saturation_top' AS ranking, seccion_id, residential_saturation_index AS score, residential_profile_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY residential_saturation_index DESC
LIMIT 5;

SELECT 'prestige_top' AS ranking, seccion_id, urban_prestige_signal AS score, prestige_label AS label
FROM marts.territorial_intelligence_section_2023
ORDER BY urban_prestige_signal DESC
LIMIT 5;

SELECT
    'adjacent_delta_check' AS qa_check,
    ROUND(MAX(ABS(a.territorial_signal_score - b.territorial_signal_score))::numeric, 2) AS max_adjacent_territorial_delta,
    ROUND(AVG(ABS(a.territorial_signal_score - b.territorial_signal_score))::numeric, 2) AS avg_adjacent_territorial_delta,
    ROUND(MAX(ABS(a.market_pressure_index - b.market_pressure_index))::numeric, 2) AS max_adjacent_pressure_delta
FROM marts.territorial_intelligence_section_2023 a
JOIN marts.territorial_intelligence_section_2023 b
  ON a.seccion_id < b.seccion_id
 AND ST_Touches(a.geom, b.geom);
