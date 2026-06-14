CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS core.mijas_contextual_priors (
    prior_id text PRIMARY KEY,
    municipality text NOT NULL DEFAULT 'mijas',
    prior_label text NOT NULL,
    applies_to text,
    prior_type text,
    expected_effect text,
    confidence text,
    evidence_type text,
    model_use text,
    caution text,
    source_document text,
    version text,
    is_active boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.mijas_section_context (
    seccion_id text PRIMARY KEY,
    municipality text DEFAULT 'mijas',
    territorial_cluster text,
    cluster_label text,
    historical_identity_score numeric,
    local_network_strength numeric,
    tourism_residential_profile numeric,
    foreign_residential_pressure numeric,
    irregular_housing_legacy numeric,
    urban_density_context numeric,
    context_confidence text,
    notes text
);

INSERT INTO core.mijas_contextual_priors (
    prior_id, prior_label, applies_to, prior_type, expected_effect, confidence,
    evidence_type, model_use, caution, source_document, version, is_active
) VALUES
    ('psoe_local_floor_strength', 'PSOE Local Floor Strength', 'PSOE', 'contextual_prior', 'positive', 'medium', 'historical_context_and_municipal_results', 'adjust_party_floor', 'Do not treat as deterministic. Validate against election data.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('pp_brand_reserve', 'PP Brand Reserve', 'PP', 'contextual_prior', 'positive', 'medium_high_if_supported_by_data', 'compare_municipal_vs_regional_national_results', 'estimate_pp_recovery_potential', 'Only apply where data confirms PP underperformance in municipal elections.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('pp_candidate_reset_potential', 'PP Candidate Reset Potential', 'PP', 'contextual_prior', 'positive', 'medium', 'leadership_change_context', 'candidate_contextual_adjustment', 'Use as a limited hypothesis-based adjustment and moderate with uncertainty.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('conservative_localist_split_risk', 'Conservative Localist Split Risk', 'PP', 'contextual_prior', 'negative', 'medium_low', 'possible_new_localist_supply', 'uncertainty_and_fragmentation_adjustment', 'Only activate after candidate or party supply is human-confirmed.', 'contextual_hypotheses.yaml', 'v1', FALSE),
    ('cs_orphan_vote_pool', 'Cs Orphan Vote Pool', 'CS', 'transfer_pool', 'uncertain', 'medium', 'observed_electoral_decline', 'vote_transfer_uncertainty', 'Do not distribute mechanically.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('pmp_localist_transfer_pool', 'Por Mi Pueblo Localist Transfer Pool', 'PMP', 'transfer_pool', 'uncertain', 'medium_low', 'observed_2023_localist_vote', 'localist_transfer_uncertainty', 'Personalist or localist vote may transfer, persist or abstain.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('vox_national_anchor', 'VOX National Anchor', 'VOX', 'contextual_prior', 'stabilizing', 'medium', 'compare_municipal_vs_regional_national_results', 'blend_municipal_with_regional_national_signal', 'Avoid purely local explanation.', 'contextual_hypotheses.yaml', 'v1', TRUE),
    ('territorial_cluster_effect', 'Territorial Cluster Effect', 'all', 'spatial_context', 'heterogeneous', 'medium_high', 'internal_expert_context_and_gis_labels', 'cluster_level_adjustments', 'Use clusters as priors, not deterministic labels.', 'contextual_hypotheses.yaml', 'v1', TRUE)
ON CONFLICT (prior_id) DO UPDATE SET
    prior_label = EXCLUDED.prior_label,
    applies_to = EXCLUDED.applies_to,
    prior_type = EXCLUDED.prior_type,
    expected_effect = EXCLUDED.expected_effect,
    confidence = EXCLUDED.confidence,
    evidence_type = EXCLUDED.evidence_type,
    model_use = EXCLUDED.model_use,
    caution = EXCLUDED.caution,
    source_document = EXCLUDED.source_document,
    version = EXCLUDED.version,
    is_active = EXCLUDED.is_active;

INSERT INTO core.mijas_section_context (
    seccion_id, territorial_cluster, cluster_label, historical_identity_score,
    local_network_strength, tourism_residential_profile,
    foreign_residential_pressure, irregular_housing_legacy,
    urban_density_context, context_confidence, notes
) VALUES
    ('2907001001', 'mijas_pueblo', 'Mijas Pueblo', 88, 86, 24, 26, 30, 28, 'medium_high', 'Internal expert context: historical nucleus.'),
    ('2907001002', 'mijas_pueblo', 'Mijas Pueblo', 88, 86, 24, 26, 30, 28, 'medium_high', 'Internal expert context: historical nucleus.'),
    ('2907001003', 'lagunas_originarias', 'Las Lagunas originarias', 54, 58, 20, 22, 26, 82, 'medium', 'Internal expert context: older dense Las Lagunas area.'),
    ('2907001004', 'lagunas_originarias', 'Las Lagunas originarias', 54, 58, 20, 22, 26, 82, 'medium', 'Internal expert context: older dense Las Lagunas area.'),
    ('2907001005', 'lagunas_originarias', 'Las Lagunas originarias', 54, 58, 20, 22, 26, 82, 'medium', 'Internal expert context: older dense Las Lagunas area.'),
    ('2907001006', 'lagunas_originarias', 'Las Lagunas originarias', 54, 58, 20, 22, 26, 82, 'medium', 'Internal expert context: older dense Las Lagunas area.'),
    ('2907001007', 'la_cala_core', 'La Cala core', 70, 68, 82, 78, 20, 52, 'medium', 'Internal expert context: coastal core.'),
    ('2907001008', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001009', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001010', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001011', 'coastal_touristic_residential', 'Coastal tourism-residential', 36, 38, 88, 86, 16, 44, 'medium', 'Internal expert context: coastal corridor.'),
    ('2907001012', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001013', 'rural_diseminado_mixed', 'Rural / dispersed mixed', 58, 62, 62, 55, 82, 24, 'medium_low', 'Internal expert context: mixed rural and residential profile.'),
    ('2907001014', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001015', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001016', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001017', 'rural_diseminado_mixed', 'Rural / dispersed mixed', 54, 58, 54, 48, 72, 32, 'medium_low', 'Internal expert context: mixed dispersed or villa expansion profile.'),
    ('2907001018', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001019', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001020', 'lagunas_expansion', 'Las Lagunas expansion', 38, 42, 24, 25, 18, 88, 'medium', 'Internal expert context: dense urban expansion.'),
    ('2907001021', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001022', 'cala_gis_context', 'La Cala GIS context', 34, 36, 68, 62, 18, 42, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001023', 'coastal_touristic_residential', 'Coastal tourism-residential', 36, 38, 88, 86, 16, 44, 'medium', 'Internal expert context: coastal corridor.'),
    ('2907001024', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001025', 'lagunas_expansion', 'Las Lagunas expansion', 38, 42, 24, 25, 18, 88, 'medium', 'Internal expert context: dense urban expansion.'),
    ('2907001026', 'diseminado_gis_context', 'Dispersed GIS context', 42, 44, 58, 54, 56, 28, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001027', 'coastal_touristic_residential', 'Coastal tourism-residential', 36, 38, 88, 86, 16, 44, 'medium', 'Internal expert context: coastal corridor.'),
    ('2907001028', 'diseminado_gis_context', 'Dispersed GIS context', 42, 44, 58, 54, 56, 28, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001029', 'lagunas_gis_context', 'Las Lagunas GIS context', 45, 48, 22, 24, 22, 68, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001030', 'coastal_touristic_residential', 'Coastal tourism-residential', 36, 38, 92, 90, 14, 48, 'medium', 'Internal expert context: coastal expansion.'),
    ('2907001031', 'cala_gis_context', 'La Cala GIS context', 34, 36, 68, 62, 18, 42, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001032', 'rural_diseminado_mixed', 'Rural / dispersed mixed', 58, 62, 62, 55, 82, 24, 'medium_low', 'Internal expert context: mixed rural and residential profile.'),
    ('2907001033', 'mixed_lagunas_coastal_or_expansion', 'Mixed Lagunas / coastal expansion', 36, 40, 54, 52, 22, 72, 'medium_low', 'Internal expert context: mixed spatial definition.'),
    ('2907001034', 'cala_gis_context', 'La Cala GIS context', 34, 36, 68, 62, 18, 42, 'medium_low', 'GIS neighborhood label only; conservative contextual profile.'),
    ('2907001035', 'rural_diseminado_mixed', 'Rural / dispersed mixed', 58, 62, 62, 55, 82, 24, 'medium_low', 'Internal expert context: mixed rural and residential profile.'),
    ('2907001036', 'urban_expansion_villa_profile', 'Urban expansion / villa profile', 42, 46, 64, 56, 30, 38, 'medium_low', 'Internal expert context: villa-oriented mixed expansion.'),
    ('2907001037', 'lagunas_expansion', 'Las Lagunas expansion', 38, 42, 24, 25, 18, 88, 'medium', 'Internal expert context: dense urban expansion.')
ON CONFLICT (seccion_id) DO UPDATE SET
    territorial_cluster = EXCLUDED.territorial_cluster,
    cluster_label = EXCLUDED.cluster_label,
    historical_identity_score = EXCLUDED.historical_identity_score,
    local_network_strength = EXCLUDED.local_network_strength,
    tourism_residential_profile = EXCLUDED.tourism_residential_profile,
    foreign_residential_pressure = EXCLUDED.foreign_residential_pressure,
    irregular_housing_legacy = EXCLUDED.irregular_housing_legacy,
    urban_density_context = EXCLUDED.urban_density_context,
    context_confidence = EXCLUDED.context_confidence,
    notes = EXCLUDED.notes;

DROP MATERIALIZED VIEW IF EXISTS marts.electoral_forecast_counterweights_2027 CASCADE;

CREATE MATERIALIZED VIEW marts.electoral_forecast_counterweights_2027 AS
WITH party_results AS (
    SELECT
        eb.election_id,
        eb.seccion_id,
        MAX((item->>'pct')::numeric * 100) FILTER (WHERE item->>'normalized_party_family' = 'PP') AS pp,
        MAX((item->>'pct')::numeric * 100) FILTER (WHERE item->>'normalized_party_family' = 'PSOE') AS psoe,
        MAX((item->>'pct')::numeric * 100) FILTER (WHERE item->>'normalized_party_family' = 'CS') AS cs,
        MAX((item->>'pct')::numeric * 100) FILTER (WHERE item->>'normalized_party_family' = 'VOX') AS vox,
        SUM((item->>'pct')::numeric * 100) FILTER (WHERE item->>'normalized_party_family' = 'LOCAL') AS localist,
        MAX((item->>'pct')::numeric * 100) FILTER (WHERE item->>'party' = 'POR MI PUEBLO') AS pmp
    FROM marts.mv_electoral_behavior eb
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) item
    GROUP BY eb.election_id, eb.seccion_id
),
pivoted AS (
    SELECT
        seccion_id,
        MAX(pp) FILTER (WHERE election_id = 11) AS pp_municipal_2015,
        MAX(pp) FILTER (WHERE election_id = 4) AS pp_municipal_2019,
        MAX(pp) FILTER (WHERE election_id = 1) AS pp_municipal_2023,
        MAX(pp) FILTER (WHERE election_id = 17) AS pp_andaluzas_2022,
        MAX(pp) FILTER (WHERE election_id = 40) AS pp_andaluzas_2026,
        MAX(pp) FILTER (WHERE election_id = 10) AS pp_congreso_2023,
        MAX(pp) FILTER (WHERE election_id = 16) AS pp_europeas_2024,
        MAX(psoe) FILTER (WHERE election_id = 11) AS psoe_municipal_2015,
        MAX(psoe) FILTER (WHERE election_id = 4) AS psoe_municipal_2019,
        MAX(psoe) FILTER (WHERE election_id = 1) AS psoe_municipal_2023,
        MAX(cs) FILTER (WHERE election_id = 11) AS cs_municipal_2015,
        MAX(cs) FILTER (WHERE election_id = 4) AS cs_municipal_2019,
        MAX(cs) FILTER (WHERE election_id = 1) AS cs_municipal_2023,
        MAX(vox) FILTER (WHERE election_id = 1) AS vox_municipal_2023,
        MAX(vox) FILTER (WHERE election_id = 40) AS vox_andaluzas_2026,
        MAX(vox) FILTER (WHERE election_id = 10) AS vox_congreso_2023,
        MAX(vox) FILTER (WHERE election_id = 16) AS vox_europeas_2024,
        MAX(localist) FILTER (WHERE election_id = 1) AS localist_municipal_2023,
        MAX(pmp) FILTER (WHERE election_id = 1) AS pmp_municipal_2023
    FROM party_results
    GROUP BY seccion_id
),
raw AS (
    SELECT
        p.seccion_id,
        c.territorial_cluster,
        c.cluster_label,
        c.context_confidence,
        ROUND(GREATEST(0,
            (
                COALESCE(p.pp_andaluzas_2022, p.pp_municipal_2023)
                + COALESCE(p.pp_andaluzas_2026, p.pp_municipal_2023)
                + COALESCE(p.pp_congreso_2023, p.pp_municipal_2023)
                + COALESCE(p.pp_europeas_2024, p.pp_municipal_2023)
            ) / 4 - COALESCE(p.pp_municipal_2023, 0)
        )::numeric, 2) AS pp_brand_reserve,
        ROUND(LEAST(100, GREATEST(0,
            100 - (
                GREATEST(COALESCE(p.psoe_municipal_2015, 0), COALESCE(p.psoe_municipal_2019, 0), COALESCE(p.psoe_municipal_2023, 0))
                - LEAST(COALESCE(p.psoe_municipal_2015, 0), COALESCE(p.psoe_municipal_2019, 0), COALESCE(p.psoe_municipal_2023, 0))
            ) * 5
            + CASE WHEN c.territorial_cluster = 'lagunas_originarias' THEN 6 ELSE 0 END
        ))::numeric, 2) AS psoe_local_floor_strength,
        ROUND(GREATEST(0, COALESCE(p.cs_municipal_2019, p.cs_municipal_2015, 0) - COALESCE(p.cs_municipal_2023, 0))::numeric, 2) AS cs_orphan_vote_pool,
        ROUND(COALESCE(p.pmp_municipal_2023, 0)::numeric, 2) AS pmp_localist_transfer_pool,
        ROUND(LEAST(100, GREATEST(0,
            COALESCE(p.localist_municipal_2023, 0) * 1.8 + COALESCE(c.local_network_strength, 50) * 0.20
        ))::numeric, 2) AS localist_overlap_signal,
        ROUND((
            COALESCE(p.vox_andaluzas_2026, p.vox_municipal_2023, 0)
            + COALESCE(p.vox_congreso_2023, p.vox_municipal_2023, 0)
            + COALESCE(p.vox_europeas_2024, p.vox_municipal_2023, 0)
        ) / 3::numeric, 2) AS vox_national_anchor,
        ROUND((
            COALESCE(c.historical_identity_score, 50) * 0.35
            + COALESCE(c.local_network_strength, 50) * 0.30
            + COALESCE(c.urban_density_context, 50) * 0.15
            + COALESCE(c.tourism_residential_profile, 50) * 0.10
            + COALESCE(c.irregular_housing_legacy, 50) * 0.10
        )::numeric, 2) AS territorial_cluster_effect
    FROM pivoted p
    JOIN core.mijas_section_context c
      ON c.seccion_id = p.seccion_id
),
counterweights AS (
    SELECT
        *,
        ROUND((pp_brand_reserve * 0.45)::numeric, 2) AS pp_candidate_reset_potential,
        0::numeric AS conservative_localist_split_risk,
        ROUND(LEAST(100, GREATEST(0,
            cs_orphan_vote_pool * 1.7
            + pmp_localist_transfer_pool * 1.8
            + localist_overlap_signal * 0.30
            + CASE WHEN context_confidence = 'medium_low' THEN 10 ELSE 4 END
        ))::numeric, 2) AS contextual_uncertainty
    FROM raw
)
SELECT
    *,
    ROUND(LEAST(4, GREATEST(-4,
        pp_brand_reserve * 0.16
        + pp_candidate_reset_potential * 0.08
        - psoe_local_floor_strength * 0.018
    ))::numeric, 2) AS contextual_vote_adjustment_pct,
    ROUND(LEAST(100, GREATEST(-100,
        pp_brand_reserve * 1.8
        + pp_candidate_reset_potential * 0.9
        - psoe_local_floor_strength * 0.20
    ))::numeric, 2) AS contextual_adjustment_score,
    CASE
        WHEN context_confidence = 'medium_high' AND contextual_uncertainty < 35 THEN 'medium_high'
        WHEN contextual_uncertainty < 58 THEN 'medium'
        ELSE 'medium_low'
    END AS contextual_confidence,
    TRUE AS has_contextual_adjustments,
    FALSE AS conservative_localist_split_is_active,
    jsonb_build_array(
        jsonb_build_object('prior', 'pp_brand_reserve', 'value', pp_brand_reserve, 'category', 'observed_cross_election_signal'),
        jsonb_build_object('prior', 'pp_candidate_reset_potential', 'value', ROUND((pp_brand_reserve * 0.45)::numeric, 2), 'category', 'contextual_hypothesis'),
        jsonb_build_object('prior', 'psoe_local_floor_strength', 'value', psoe_local_floor_strength, 'category', 'observed_municipal_stability_with_context'),
        jsonb_build_object('prior', 'cs_orphan_vote_pool', 'value', cs_orphan_vote_pool, 'category', 'uncertain_transfer_pool'),
        jsonb_build_object('prior', 'pmp_localist_transfer_pool', 'value', pmp_localist_transfer_pool, 'category', 'uncertain_transfer_pool'),
        jsonb_build_object('prior', 'conservative_localist_split_risk', 'value', 0, 'category', 'inactive_until_human_confirmation')
    ) AS contextual_drivers
FROM counterweights;

CREATE UNIQUE INDEX IF NOT EXISTS ux_electoral_forecast_counterweights_2027
    ON marts.electoral_forecast_counterweights_2027 (seccion_id);

COMMENT ON MATERIALIZED VIEW marts.electoral_forecast_counterweights_2027 IS
    'Bounded Mijas 2027 contextual counterweights. Context is hypothesis metadata subordinate to observed electoral data; transfer pools are not distributed mechanically.';
