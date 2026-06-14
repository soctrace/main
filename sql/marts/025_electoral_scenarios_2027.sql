CREATE SCHEMA IF NOT EXISTS marts;

DROP MATERIALIZED VIEW IF EXISTS marts.electoral_scenarios_2027 CASCADE;

CREATE MATERIALIZED VIEW marts.electoral_scenarios_2027 AS
WITH municipal AS (
    SELECT *
    FROM marts.electoral_forecasting_municipality_2027
    WHERE municipality_id = '29070'
),
counterweight_summary AS (
    SELECT
        AVG(pp_brand_reserve) AS pp_brand_reserve,
        AVG(pp_candidate_reset_potential) AS pp_candidate_reset_potential,
        AVG(cs_orphan_vote_pool) AS cs_orphan_vote_pool,
        AVG(pmp_localist_transfer_pool) AS pmp_localist_transfer_pool,
        AVG(contextual_uncertainty) AS contextual_uncertainty
    FROM marts.electoral_forecast_counterweights_2027
),
priority_sections AS (
    SELECT jsonb_agg(
        jsonb_build_object(
            'section_id', seccion_id,
            'swing_sections', swing_sections,
            'abstention_risk', abstention_risk,
            'forecast_confidence', forecast_confidence
        )
        ORDER BY is_strategic_section DESC, swing_sections DESC, abstention_risk DESC, seccion_id
    ) AS sections
    FROM (
        SELECT *
        FROM marts.electoral_forecasting_ui_2027
        ORDER BY is_strategic_section DESC, swing_sections DESC, abstention_risk DESC, seccion_id
        LIMIT 8
    ) ranked
),
scenario_parameters AS (
    SELECT *
    FROM (VALUES
        (
            'structural',
            'Structural Forecast',
            'Structural',
            'Internal structural baseline based on historical electoral behavior, synthetic socioeconomic indicators and territorial features.',
            'Bounded structural and contextual baseline. Local priors remain hypotheses, not facts.',
            1.00::numeric,
            1.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            FALSE,
            'The structural forecast shows the current internally modeled baseline. It is an estimated scenario, not a closed prediction.'
        ),
        (
            'candidate_reset',
            'Candidate Reset Scenario',
            'Candidate Reset',
            'Tests a bounded PP recovery after local leadership renewal while treating Cs and PMP as uncertain transfer pools.',
            'PP recovers part of its local brand reserve. Cs and PMP remain uncertain electoral supplies; their votes are not transferred mechanically.',
            0.35::numeric,
            0.90::numeric,
            0.45::numeric,
            0.20::numeric,
            0.20::numeric,
            0.00::numeric,
            6.00::numeric,
            FALSE,
            'This scenario increases the relevance of PP brand reserve and tests whether leadership renewal could reduce previous local underperformance.'
        ),
        (
            'localist_fragmentation',
            'Localist Fragmentation Scenario',
            'Localist Split',
            'Conditional scenario testing whether a conservative localist supply could fragment part of the center-right recovery potential.',
            'A hypothetical conservative localist supply captures part of the PP recovery potential. This is conditional and does not assert a confirmed candidacy.',
            0.75::numeric,
            1.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            1.00::numeric,
            14.00::numeric,
            FALSE,
            'This conditional scenario tests whether a conservative localist split could fragment the center-right vote and increase uncertainty.'
        ),
        (
            'oraculum_ready',
            'Oraculum-ready Scenario',
            'Oraculum-ready',
            'Scenario prepared for future Oraculum calibration. No polling inputs have been applied yet.',
            'Preserves the current baseline and identifies priority sections for future field validation. It does not invent polling inputs.',
            1.00::numeric,
            1.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            0.00::numeric,
            2.00::numeric,
            FALSE,
            'This scenario identifies where field validation would most improve forecast reliability. No Oraculum polling inputs have been applied.'
        )
    ) AS scenarios(
        scenario_id,
        scenario_name,
        scenario_label,
        scenario_description,
        scenario_assumption,
        cs_retained_share,
        pmp_retained_share,
        cs_to_pp_share,
        cs_to_psoe_share,
        pmp_to_pp_share,
        localist_split_factor,
        uncertainty_addition,
        scenario_oraculum_calibrated,
        scenario_interpretation
    )
),
scenario_context AS (
    SELECT
        m.*,
        p.*,
        c.pp_brand_reserve,
        c.pp_candidate_reset_potential,
        c.cs_orphan_vote_pool,
        c.pmp_localist_transfer_pool,
        c.contextual_uncertainty AS baseline_contextual_uncertainty,
        LEAST(100, GREATEST(0, c.cs_orphan_vote_pool * 1.70)) AS cs_supply_uncertainty,
        LEAST(100, GREATEST(0, c.pmp_localist_transfer_pool * 1.80)) AS pmp_supply_uncertainty,
        CASE WHEN p.scenario_id = 'localist_fragmentation' THEN 72 ELSE 28 END::numeric AS localist_supply_uncertainty,
        CASE WHEN p.scenario_id = 'candidate_reset' THEN 64 ELSE 30 END::numeric AS candidate_supply_uncertainty,
        LEAST(4, c.pp_candidate_reset_potential * 0.45 + c.pp_brand_reserve * 0.12) AS candidate_reset_bonus,
        LEAST(4, c.pp_brand_reserve * 0.25 + c.pp_candidate_reset_potential * 0.25) AS localist_split_transfer
    FROM municipal m
    CROSS JOIN counterweight_summary c
    CROSS JOIN scenario_parameters p
),
party_shares AS (
    SELECT
        s.*,
        party_item->>'party' AS party,
        (party_item->>'projected_vote_share')::numeric AS baseline_share
    FROM scenario_context s
    CROSS JOIN LATERAL jsonb_array_elements(s.projected_vote_shares) party_item
),
adjusted_party_shares AS (
    SELECT
        *,
        CASE
            WHEN scenario_id IN ('structural', 'oraculum_ready') THEN baseline_share
            WHEN scenario_id = 'candidate_reset' AND party = 'PP' THEN
                baseline_share
                + candidate_reset_bonus
                + COALESCE(MAX(baseline_share) FILTER (WHERE party = 'CS') OVER (), 0) * (1 - cs_retained_share) * cs_to_pp_share
                + COALESCE(MAX(baseline_share) FILTER (WHERE party = 'POR MI PUEBLO') OVER (), 0) * (1 - pmp_retained_share) * pmp_to_pp_share
            WHEN scenario_id = 'candidate_reset' AND party = 'PSOE-A' THEN
                baseline_share
                + COALESCE(MAX(baseline_share) FILTER (WHERE party = 'CS') OVER (), 0) * (1 - cs_retained_share) * cs_to_psoe_share
            WHEN scenario_id = 'candidate_reset' AND party = 'CS' THEN baseline_share * cs_retained_share
            WHEN scenario_id = 'candidate_reset' AND party = 'POR MI PUEBLO' THEN baseline_share * pmp_retained_share
            WHEN scenario_id = 'localist_fragmentation' AND party = 'PP' THEN baseline_share - localist_split_transfer
            WHEN scenario_id = 'localist_fragmentation' AND party = 'POR MI PUEBLO' THEN baseline_share + localist_split_transfer
            WHEN scenario_id = 'localist_fragmentation' AND party = 'CS' THEN baseline_share * cs_retained_share
            ELSE baseline_share
        END AS adjusted_share
    FROM party_shares
),
normalized_party_shares AS (
    SELECT
        *,
        ROUND(100 * adjusted_share / NULLIF(SUM(adjusted_share) OVER (PARTITION BY scenario_id), 0), 2) AS normalized_share
    FROM adjusted_party_shares
),
scenario_vote_shares AS (
    SELECT
        scenario_id,
        jsonb_agg(
            jsonb_build_object('party', party, 'projected_vote_share', normalized_share)
            ORDER BY normalized_share DESC, party
        ) AS projected_vote_shares
    FROM normalized_party_shares
    GROUP BY scenario_id
),
scenario_leaders AS (
    SELECT DISTINCT ON (scenario_id)
        scenario_id,
        party AS projected_leading_party,
        normalized_share AS projected_leading_vote_share
    FROM normalized_party_shares
    ORDER BY scenario_id, normalized_share DESC, party
)
SELECT
    s.municipality_id,
    2027 AS forecast_year,
    s.scenario_id,
    s.scenario_name,
    s.scenario_label,
    s.scenario_description,
    s.scenario_assumption,
    CASE
        WHEN s.scenario_id = 'candidate_reset' THEN ROUND((s.turnout_forecast - 0.60)::numeric, 2)
        ELSE s.turnout_forecast
    END AS turnout_forecast,
    CASE
        WHEN s.scenario_id = 'candidate_reset' THEN ROUND(LEAST(100, s.volatility + 3)::numeric, 2)
        WHEN s.scenario_id = 'localist_fragmentation' THEN ROUND(LEAST(100, s.volatility + 7)::numeric, 2)
        ELSE s.volatility
    END AS volatility,
    ROUND(LEAST(100, GREATEST(0,
        s.forecast_confidence - s.uncertainty_addition * 0.45
    ))::numeric, 2) AS forecast_confidence,
    ROUND(LEAST(100, GREATEST(0,
        s.contextual_uncertainty + s.uncertainty_addition
    ))::numeric, 2) AS contextual_uncertainty,
    s.swing_territory_count
        + CASE WHEN s.scenario_id = 'candidate_reset' THEN 1 WHEN s.scenario_id = 'localist_fragmentation' THEN 2 ELSE 0 END
        AS swing_territory_count,
    s.strategic_section_count
        + CASE WHEN s.scenario_id = 'localist_fragmentation' THEN 2 ELSE 0 END
        AS strategic_section_count,
    shares.projected_vote_shares,
    leader.projected_leading_party,
    leader.projected_leading_vote_share,
    s.scenario_oraculum_calibrated AS oraculum_calibrated,
    'electoral_scenarios_2027_v1'::text AS model_version,
    s.scenario_interpretation AS interpretation,
    ROUND(s.cs_supply_uncertainty::numeric, 2) AS cs_supply_uncertainty,
    ROUND(s.pmp_supply_uncertainty::numeric, 2) AS pmp_supply_uncertainty,
    ROUND(s.localist_supply_uncertainty::numeric, 2) AS localist_supply_uncertainty,
    ROUND(s.candidate_supply_uncertainty::numeric, 2) AS candidate_supply_uncertainty,
    s.scenario_id = 'localist_fragmentation' AS is_conditional,
    s.scenario_id <> 'structural' AS has_contextual_adjustments,
    CASE
        WHEN s.scenario_id = 'oraculum_ready' THEN priority.sections
        ELSE '[]'::jsonb
    END AS oraculum_priority_sections
FROM scenario_context s
JOIN scenario_vote_shares shares USING (scenario_id)
JOIN scenario_leaders leader USING (scenario_id)
CROSS JOIN priority_sections priority;

CREATE UNIQUE INDEX IF NOT EXISTS ux_electoral_scenarios_2027
    ON marts.electoral_scenarios_2027 (municipality_id, scenario_id);

COMMENT ON MATERIALIZED VIEW marts.electoral_scenarios_2027 IS
    'Comparable, bounded and auditable Mijas municipal scenarios for 2027. Scenario assumptions are hypotheses, not confirmed candidacies or polling inputs.';
