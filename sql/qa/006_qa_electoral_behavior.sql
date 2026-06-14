WITH target AS (
    SELECT *
    FROM marts.mv_electoral_behavior
    WHERE anio = 2023
      AND election_id = 1
      AND LEFT(seccion_id, 5) = '29070'
),
party_json AS (
    SELECT
        t.seccion_id,
        COUNT(*) AS party_count,
        SUM((party_result ->> 'pct')::numeric) AS pct_sum
    FROM target t
    CROSS JOIN LATERAL JSONB_ARRAY_ELEMENTS(t.party_results_json) AS party_result
    GROUP BY t.seccion_id
)
SELECT
    'sections_2023' AS check_name,
    COUNT(*)::numeric AS value,
    37::numeric AS expected,
    COUNT(*) = 37 AS passed
FROM target

UNION ALL

SELECT
    'missing_winning_party',
    COUNT(*) FILTER (WHERE winning_party IS NULL)::numeric,
    0::numeric,
    COUNT(*) FILTER (WHERE winning_party IS NULL) = 0
FROM target

UNION ALL

SELECT
    'missing_party_results_json',
    COUNT(*) FILTER (
        WHERE party_results_json IS NULL
           OR JSONB_ARRAY_LENGTH(party_results_json) = 0
    )::numeric,
    0::numeric,
    COUNT(*) FILTER (
        WHERE party_results_json IS NULL
           OR JSONB_ARRAY_LENGTH(party_results_json) = 0
    ) = 0
FROM target

UNION ALL

SELECT
    'sections_with_10_parties',
    COUNT(*) FILTER (WHERE pj.party_count = 10)::numeric,
    COUNT(*)::numeric,
    COUNT(*) FILTER (WHERE pj.party_count = 10) = COUNT(*)
FROM party_json pj

UNION ALL

SELECT
    'pct_sum_near_100',
    COUNT(*) FILTER (WHERE ABS(pj.pct_sum - 100) <= 0.5)::numeric,
    COUNT(*)::numeric,
    COUNT(*) FILTER (WHERE ABS(pj.pct_sum - 100) <= 0.5) = COUNT(*)
FROM party_json pj

UNION ALL

SELECT
    'negative_victory_margin',
    COUNT(*) FILTER (WHERE victory_margin_pct < 0)::numeric,
    0::numeric,
    COUNT(*) FILTER (WHERE victory_margin_pct < 0) = 0
FROM target

UNION ALL

SELECT
    'competitive_parties_count_lt_1',
    COUNT(*) FILTER (WHERE competitive_parties_count < 1)::numeric,
    0::numeric,
    COUNT(*) FILTER (WHERE competitive_parties_count < 1) = 0
FROM target

UNION ALL

SELECT
    'concentration_out_of_range',
    COUNT(*) FILTER (
        WHERE vote_concentration_index < 0
           OR vote_concentration_index > 1
    )::numeric,
    0::numeric,
    COUNT(*) FILTER (
        WHERE vote_concentration_index < 0
           OR vote_concentration_index > 1
    ) = 0
FROM target

UNION ALL

SELECT
    'local_national_regional_coherence',
    COUNT(*) FILTER (
        WHERE ABS(local_vote_pct + national_vote_pct + regional_other_vote_pct - 100) <= 0.6
    )::numeric,
    COUNT(*)::numeric,
    COUNT(*) FILTER (
        WHERE ABS(local_vote_pct + national_vote_pct + regional_other_vote_pct - 100) <= 0.6
    ) = COUNT(*)
FROM target;

SELECT
    seccion_id,
    winning_party,
    winning_party_pct,
    runner_up_party,
    runner_up_pct,
    victory_margin_pct,
    local_vote_pct,
    national_vote_pct,
    left_bloc_pct,
    right_bloc_pct,
    competitive_parties_count,
    vote_concentration_index,
    party_results_json
FROM marts.mv_electoral_behavior
WHERE anio = 2023
  AND election_id = 1
  AND LEFT(seccion_id, 5) = '29070'
ORDER BY seccion_id
LIMIT 5;
