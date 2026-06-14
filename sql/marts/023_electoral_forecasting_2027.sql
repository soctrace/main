CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS core.agent_audit_log (
    audit_id bigserial PRIMARY KEY,
    question text NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT NOW(),
    municipality_id text,
    section_id text,
    datasets_used jsonb NOT NULL DEFAULT '[]'::jsonb,
    variables_used jsonb NOT NULL DEFAULT '[]'::jsonb,
    models_used jsonb NOT NULL DEFAULT '[]'::jsonb,
    confidence_level text NOT NULL,
    response_category text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

DROP MATERIALIZED VIEW IF EXISTS marts.electoral_forecasting_ui_2027 CASCADE;
DROP MATERIALIZED VIEW IF EXISTS marts.electoral_forecasting_features_2027 CASCADE;
DROP VIEW IF EXISTS marts.electoral_forecasting_municipality_2027 CASCADE;

CREATE MATERIALIZED VIEW marts.electoral_forecasting_features_2027 AS
/*
Structural baseline for the 2027 municipal election. This is an estimated
scenario, not polling and not a claim about future events. It uses approved
internal marts only. Future Oraculum calibration must enter through the
reserved calibration fields exposed by this mart.
*/
WITH latest_municipal AS (
    SELECT *
    FROM marts.mv_electoral_behavior
    WHERE tipo_eleccion_code = 'MUNICIPALES'
      AND anio = 2023
),
municipal_history AS (
    SELECT
        seccion_id,
        COUNT(*) AS historical_elections,
        STDDEV_POP(participacion) AS turnout_stddev,
        AVG(participacion) AS turnout_mean,
        AVG(victory_margin_pct) AS victory_margin_mean,
        AVG(fragmentation_index) AS fragmentation_mean
    FROM marts.mv_electoral_behavior
    WHERE tipo_eleccion_code = 'MUNICIPALES'
      AND anio <= 2023
    GROUP BY seccion_id
),
base AS (
    SELECT
        e.seccion_id,
        LEFT(e.seccion_id, 5) AS municipality_id,
        2027 AS forecast_year,
        e.winning_party AS structural_projected_leading_party,
        ROUND(e.winning_party_pct::numeric, 2) AS structural_projected_vote_share,
        (
            SELECT SUM((item->>'pct')::numeric * 100)
            FROM jsonb_array_elements(COALESCE(e.party_results_json, '[]'::jsonb)) item
            WHERE item->>'normalized_party_family' = 'PP'
        ) AS structural_pp_vote_share,
        (
            SELECT SUM((item->>'pct')::numeric * 100)
            FROM jsonb_array_elements(COALESCE(e.party_results_json, '[]'::jsonb)) item
            WHERE item->>'normalized_party_family' = 'PSOE'
        ) AS structural_psoe_vote_share,
        e.party_results_json AS projected_party_results_json,
        e.votos_validos AS baseline_valid_votes,
        e.participacion * 100 AS observed_turnout_2023,
        e.victory_margin_pct,
        e.fragmentation_index,
        e.competitive_parties_count,
        e.local_vote_pct,
        e.localism_index,
        h.historical_elections,
        h.turnout_stddev * 100 AS turnout_stddev,
        h.turnout_mean * 100 AS turnout_mean,
        h.victory_margin_mean,
        h.fragmentation_mean,
        sis.vulnerability_index,
        sis.resilience_index,
        sis.inequality_pressure_index,
        sis.human_capital_index,
        sis.productive_complexity_index,
        sis.human_capital_completeness_pct,
        sis.vulnerability_completeness_pct,
        sis.resilience_completeness_pct,
        sis.productive_complexity_completeness_pct,
        sis.inequality_pressure_completeness_pct,
        hi.housing_stress_index,
        hi.market_pressure_index,
        hi.residential_stability_proxy,
        hi.methodological_confidence_score AS housing_confidence,
        cw.pp_brand_reserve,
        cw.pp_candidate_reset_potential,
        cw.conservative_localist_split_risk,
        cw.psoe_local_floor_strength,
        cw.cs_orphan_vote_pool,
        cw.pmp_localist_transfer_pool,
        cw.vox_national_anchor,
        cw.territorial_cluster_effect,
        cw.contextual_adjustment_score,
        cw.contextual_vote_adjustment_pct,
        cw.contextual_uncertainty,
        cw.contextual_confidence,
        cw.has_contextual_adjustments,
        cw.conservative_localist_split_is_active,
        cw.contextual_drivers
    FROM latest_municipal e
    LEFT JOIN municipal_history h
      ON h.seccion_id = e.seccion_id
    LEFT JOIN marts.socioeconomic_intelligence_signals sis
      ON sis.seccion_id = e.seccion_id
     AND sis.anio = 2023
    LEFT JOIN marts.housing_intelligence_features_2023 hi
      ON hi.seccion_id = e.seccion_id
     AND hi.anio = 2023
    LEFT JOIN marts.electoral_forecast_counterweights_2027 cw
      ON cw.seccion_id = e.seccion_id
),
scores AS (
    SELECT
        *,
        ROUND(LEAST(100, GREATEST(0,
            0.72 * COALESCE(observed_turnout_2023, turnout_mean, 60)
            + 0.28 * COALESCE(turnout_mean, observed_turnout_2023, 60)
        ))::numeric, 2) AS turnout_forecast,
        ROUND(LEAST(100, GREATEST(0,
            0.34 * LEAST(100, COALESCE(turnout_stddev, 0) * 8)
            + 0.30 * (100 - LEAST(100, COALESCE(victory_margin_pct, 0) * 4))
            + 0.20 * LEAST(100, COALESCE(fragmentation_index, fragmentation_mean, 0) * 100)
            + 0.16 * LEAST(100, COALESCE(competitive_parties_count, 0) * 20)
        ))::numeric, 2) AS volatility,
        ROUND(LEAST(100, GREATEST(0,
            0.58 * (100 - COALESCE(observed_turnout_2023, turnout_mean, 60))
            + 0.18 * COALESCE(vulnerability_index, 50)
            + 0.14 * COALESCE(housing_stress_index, 50)
            + 0.10 * COALESCE(inequality_pressure_index, 50)
        ))::numeric, 2) AS abstention_risk,
        ROUND(LEAST(100, GREATEST(0,
            0.74 * COALESCE(localism_index, local_vote_pct, 0)
            + 0.14 * LEAST(100, COALESCE(fragmentation_index, 0) * 100)
            + 0.12 * LEAST(100, COALESCE(competitive_parties_count, 0) * 20)
        ))::numeric, 2) AS localist_potential,
        (
            COALESCE(human_capital_completeness_pct, 0)
            + COALESCE(vulnerability_completeness_pct, 0)
            + COALESCE(resilience_completeness_pct, 0)
            + COALESCE(productive_complexity_completeness_pct, 0)
            + COALESCE(inequality_pressure_completeness_pct, 0)
        ) / 5 AS socioeconomic_completeness
    FROM base
),
final_scores AS (
    SELECT
        *,
        ROUND(LEAST(100, GREATEST(0,
            0.50 * (100 - LEAST(100, COALESCE(victory_margin_pct, 0) * 4))
            + 0.30 * volatility
            + 0.20 * LEAST(100, COALESCE(competitive_parties_count, 0) * 20)
        ))::numeric, 2) AS swing_sections,
        ROUND(LEAST(100, GREATEST(0,
            0.30 * LEAST(100, COALESCE(historical_elections, 0) * 33.33)
            + 0.24 * COALESCE(socioeconomic_completeness, 0)
            + 0.18 * COALESCE(housing_confidence, 0.55) * 100
            + 0.16 * (100 - volatility)
            + 0.12 * (100 - LEAST(100, COALESCE(turnout_stddev, 0) * 8))
        ))::numeric, 2) AS structural_forecast_confidence
    FROM scores
),
contextualized_scores AS (
    SELECT
        *,
        ROUND(LEAST(100, GREATEST(0,
            COALESCE(structural_pp_vote_share, 0) + COALESCE(contextual_vote_adjustment_pct, 0)
        ))::numeric, 2) AS final_pp_vote_share,
        ROUND(LEAST(100, GREATEST(0,
            COALESCE(structural_psoe_vote_share, 0) - COALESCE(contextual_vote_adjustment_pct, 0)
        ))::numeric, 2) AS final_psoe_vote_share
    FROM final_scores
)
SELECT
    *,
    CASE WHEN final_pp_vote_share >= final_psoe_vote_share THEN 'PP' ELSE 'PSOE-A' END AS projected_leading_party,
    GREATEST(final_pp_vote_share, final_psoe_vote_share) AS projected_vote_share,
    ROUND(LEAST(100, GREATEST(0,
        structural_forecast_confidence - COALESCE(contextual_uncertainty, 0) * 0.16
    ))::numeric, 2) AS forecast_confidence,
    CASE
        WHEN structural_forecast_confidence - COALESCE(contextual_uncertainty, 0) * 0.16 >= 75 THEN 'high'
        WHEN structural_forecast_confidence - COALESCE(contextual_uncertainty, 0) * 0.16 >= 55 THEN 'medium'
        ELSE 'low'
    END AS confidence_level,
    CASE
        WHEN swing_sections >= 68 OR abstention_risk >= 62 THEN TRUE
        ELSE FALSE
    END AS is_strategic_section,
    CASE
        WHEN swing_sections >= 60 THEN TRUE
        ELSE FALSE
    END AS is_swing_section,
    CASE
        WHEN abstention_risk >= 58 THEN TRUE
        ELSE FALSE
    END AS is_abstention_risk_area,
    CASE
        WHEN swing_sections >= 68 AND abstention_risk >= 58 AND localist_potential >= 38
            THEN 'This section combines elevated swing potential, abstention risk and localist potential. Contextual priors add bounded uncertainty and do not replace the structural model.'
        WHEN swing_sections >= 60
            THEN 'This section has a competitive structural baseline. Validated local contextual priors add a bounded adjustment; mobilization and local dynamics remain uncertain.'
        WHEN abstention_risk >= 58
            THEN 'This section shows elevated abstention risk in the structural baseline. The estimated tendency should be interpreted with turnout uncertainty.'
        ELSE 'This section shows a comparatively consolidated structural tendency, while remaining an estimated scenario rather than a certain outcome.'
    END AS interpretation,
    jsonb_build_array(
        jsonb_build_object('variable', 'victory_margin_pct', 'value', victory_margin_pct, 'category', 'observed_data'),
        jsonb_build_object('variable', 'turnout_stddev', 'value', turnout_stddev, 'category', 'model_interpretation'),
        jsonb_build_object('variable', 'vulnerability_index', 'value', vulnerability_index, 'category', 'estimated_data'),
        jsonb_build_object('variable', 'housing_stress_index', 'value', housing_stress_index, 'category', 'estimated_data'),
        jsonb_build_object('variable', 'contextual_vote_adjustment_pct', 'value', contextual_vote_adjustment_pct, 'category', 'contextual_hypothesis')
    ) AS drivers,
    jsonb_build_object(
        'observed_data', ARRAY['marts.mv_electoral_behavior'],
        'estimated_data', ARRAY['marts.socioeconomic_intelligence_signals', 'marts.housing_intelligence_features_2023'],
        'forecast_data', ARRAY['marts.electoral_forecasting_features_2027'],
        'historical_context', ARRAY['municipality_packs/mijas/contextual_hypotheses.yaml'],
        'model_interpretation', ARRAY['structural baseline with bounded contextual counterweights; no polling calibration']
    ) AS evidence_categories,
    'electoral_structural_baseline_2027_v1'::text AS model_version,
    FALSE AS oraculum_calibrated,
    NULL::text AS oraculum_calibration_version
FROM contextualized_scores;

CREATE UNIQUE INDEX IF NOT EXISTS ux_electoral_forecasting_features_2027
    ON marts.electoral_forecasting_features_2027 (seccion_id);

CREATE MATERIALIZED VIEW marts.electoral_forecasting_ui_2027 AS
SELECT
    seccion_id,
    municipality_id,
    forecast_year,
    structural_projected_leading_party,
    structural_projected_vote_share,
    structural_pp_vote_share,
    structural_psoe_vote_share,
    final_pp_vote_share,
    final_psoe_vote_share,
    projected_leading_party,
    projected_vote_share,
    turnout_forecast,
    volatility,
    abstention_risk,
    localist_potential,
    swing_sections,
    structural_forecast_confidence,
    forecast_confidence,
    confidence_level,
    is_strategic_section,
    is_swing_section,
    is_abstention_risk_area,
    interpretation,
    drivers,
    pp_brand_reserve,
    pp_candidate_reset_potential,
    conservative_localist_split_risk,
    psoe_local_floor_strength,
    cs_orphan_vote_pool,
    pmp_localist_transfer_pool,
    vox_national_anchor,
    territorial_cluster_effect,
    contextual_adjustment_score,
    contextual_vote_adjustment_pct,
    contextual_uncertainty,
    contextual_confidence,
    has_contextual_adjustments,
    conservative_localist_split_is_active,
    contextual_drivers,
    model_version,
    oraculum_calibrated
FROM marts.electoral_forecasting_features_2027;

CREATE UNIQUE INDEX IF NOT EXISTS ux_electoral_forecasting_ui_2027
    ON marts.electoral_forecasting_ui_2027 (seccion_id);

CREATE VIEW marts.electoral_forecasting_municipality_2027 AS
WITH section_summary AS (
    SELECT
        municipality_id,
        COUNT(*) AS section_count,
        COUNT(*) FILTER (WHERE is_swing_section) AS swing_territory_count,
        COUNT(*) FILTER (WHERE is_strategic_section) AS strategic_section_count,
        COUNT(*) FILTER (WHERE is_abstention_risk_area) AS abstention_risk_area_count,
        ROUND(AVG(turnout_forecast), 2) AS turnout_forecast,
        ROUND(AVG(volatility), 2) AS volatility,
        ROUND(AVG(forecast_confidence), 2) AS forecast_confidence,
        ROUND(AVG(structural_forecast_confidence), 2) AS structural_forecast_confidence,
        ROUND(AVG(contextual_vote_adjustment_pct), 2) AS contextual_vote_adjustment_pct,
        ROUND(AVG(contextual_uncertainty), 2) AS contextual_uncertainty,
        BOOL_OR(has_contextual_adjustments) AS has_contextual_adjustments
    FROM marts.electoral_forecasting_features_2027
    GROUP BY municipality_id
),
party_shares AS (
    SELECT
        f.municipality_id,
        party_item->>'party' AS party,
        ROUND(
            100 * SUM(
                CASE
                    WHEN party_item->>'normalized_party_family' = 'PP'
                        THEN f.baseline_valid_votes * f.final_pp_vote_share / 100
                    WHEN party_item->>'normalized_party_family' = 'PSOE'
                        THEN f.baseline_valid_votes * f.final_psoe_vote_share / 100
                    ELSE (party_item->>'votes')::numeric
                END
            )
            / NULLIF(SUM(SUM(
                CASE
                    WHEN party_item->>'normalized_party_family' = 'PP'
                        THEN f.baseline_valid_votes * f.final_pp_vote_share / 100
                    WHEN party_item->>'normalized_party_family' = 'PSOE'
                        THEN f.baseline_valid_votes * f.final_psoe_vote_share / 100
                    ELSE (party_item->>'votes')::numeric
                END
            )) OVER (PARTITION BY f.municipality_id), 0),
            2
        ) AS projected_vote_share
    FROM marts.electoral_forecasting_features_2027 f
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(f.projected_party_results_json, '[]'::jsonb)) AS party_item
    GROUP BY f.municipality_id, party_item->>'party'
),
party_json AS (
    SELECT
        municipality_id,
        jsonb_agg(
            jsonb_build_object('party', party, 'projected_vote_share', projected_vote_share)
            ORDER BY projected_vote_share DESC, party
        ) AS projected_vote_shares
    FROM party_shares
    GROUP BY municipality_id
)
SELECT
    s.*,
    p.projected_vote_shares,
    p.projected_vote_shares->0->>'party' AS projected_leading_party,
    (p.projected_vote_shares->0->>'projected_vote_share')::numeric AS projected_leading_vote_share,
    CASE
        WHEN s.forecast_confidence >= 75 THEN 'high'
        WHEN s.forecast_confidence >= 55 THEN 'medium'
        ELSE 'low'
    END AS confidence_level,
    'Municipal forecast combines an internal structural baseline with bounded local contextual priors. Contextual priors are hypotheses, not facts. It is not polling and has not been calibrated with Oraculum inputs.'::text AS interpretation,
    'electoral_structural_baseline_2027_v1'::text AS model_version,
    FALSE AS oraculum_calibrated
FROM section_summary s
LEFT JOIN party_json p USING (municipality_id);

COMMENT ON MATERIALIZED VIEW marts.electoral_forecasting_features_2027 IS
    'Section-level estimated structural baseline for Mijas municipal election 2027. Internal approved marts only; no polling or autonomous external learning.';

COMMENT ON VIEW marts.electoral_forecasting_municipality_2027 IS
    'Municipality aggregation of the 2027 electoral structural baseline with interpreted outputs and confidence.';
