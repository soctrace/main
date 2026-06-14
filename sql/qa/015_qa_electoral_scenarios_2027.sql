\echo 'QA electoral scenarios 2027'

SELECT COUNT(*) AS scenario_count
FROM marts.electoral_scenarios_2027;

SELECT scenario_id, scenario_label, projected_leading_party, projected_leading_vote_share,
       forecast_confidence, contextual_uncertainty, is_conditional, oraculum_calibrated
FROM marts.electoral_scenarios_2027
ORDER BY scenario_id;

SELECT
    COUNT(*) FILTER (WHERE projected_vote_shares IS NULL OR jsonb_array_length(projected_vote_shares) = 0) AS missing_vote_shares,
    COUNT(*) FILTER (WHERE forecast_confidence IS NULL) AS missing_confidence,
    COUNT(*) FILTER (WHERE interpretation IS NULL OR interpretation = '') AS missing_interpretation,
    COUNT(*) FILTER (WHERE scenario_id IS NULL OR scenario_name IS NULL OR scenario_assumption IS NULL) AS missing_critical_fields,
    COUNT(*) - COUNT(DISTINCT scenario_id) AS duplicate_scenario_ids
FROM marts.electoral_scenarios_2027;

WITH totals AS (
    SELECT
        scenario_id,
        SUM((item->>'projected_vote_share')::numeric) AS projected_vote_share_total
    FROM marts.electoral_scenarios_2027
    CROSS JOIN LATERAL jsonb_array_elements(projected_vote_shares) item
    GROUP BY scenario_id
)
SELECT scenario_id, projected_vote_share_total
FROM totals
WHERE projected_vote_share_total NOT BETWEEN 99.90 AND 100.10
ORDER BY scenario_id;

SELECT COUNT(*) AS invalid_oraculum_ready_rows
FROM marts.electoral_scenarios_2027
WHERE scenario_id = 'oraculum_ready'
  AND oraculum_calibrated;

SELECT COUNT(*) AS invalid_localist_uncertainty_rows
FROM marts.electoral_scenarios_2027 localist
JOIN marts.electoral_scenarios_2027 structural
  ON structural.municipality_id = localist.municipality_id
 AND structural.scenario_id = 'structural'
WHERE localist.scenario_id = 'localist_fragmentation'
  AND localist.contextual_uncertainty < structural.contextual_uncertainty;

SELECT COUNT(*) AS unchanged_candidate_reset_rows
FROM marts.electoral_scenarios_2027 candidate
JOIN marts.electoral_scenarios_2027 structural
  ON structural.municipality_id = candidate.municipality_id
 AND structural.scenario_id = 'structural'
WHERE candidate.scenario_id = 'candidate_reset'
  AND candidate.projected_vote_shares = structural.projected_vote_shares;
