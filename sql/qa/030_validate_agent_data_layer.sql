SELECT 'agent_section_lookup_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_section_lookup
WHERE municipio_id = '29070';

SELECT 'agent_population_age_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_population_age
WHERE municipio_id = '29070';

SELECT 'agent_section_profile_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_section_profile
WHERE municipio_id = '29070';

SELECT 'agent_electoral_results_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_electoral_results
WHERE municipio_id = '29070';

SELECT 'agent_electoral_summary_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_electoral_summary
WHERE municipio_id = '29070';

SELECT 'agent_income_sources_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_income_sources
WHERE municipio_id = '29070';

SELECT 'agent_housing_profile_rows' AS check_name, COUNT(*) AS value
FROM marts.agent_housing_profile
WHERE municipio_id = '29070';

SELECT
    year,
    COUNT(*) AS rows,
    COUNT(DISTINCT section_id) AS sections
FROM marts.agent_section_profile
WHERE municipio_id = '29070'
GROUP BY year
ORDER BY year;

SELECT
    COUNT(*) FILTER (WHERE population_total IS NOT NULL) AS population_total_not_null,
    COUNT(*) FILTER (WHERE average_age IS NOT NULL) AS average_age_not_null,
    COUNT(*) FILTER (WHERE population_over_65 IS NOT NULL) AS population_over_65_not_null,
    COUNT(*) FILTER (WHERE income_individual IS NOT NULL) AS income_individual_not_null,
    COUNT(*) FILTER (WHERE abstention_pct IS NOT NULL) AS abstention_pct_not_null,
    COUNT(*) FILTER (WHERE winner_party IS NOT NULL) AS winner_party_not_null,
    COUNT(*) FILTER (WHERE market_price_estimated_m2 IS NOT NULL) AS market_price_estimated_m2_not_null
FROM marts.agent_section_profile
WHERE municipio_id = '29070';

SELECT
    election_type,
    election_year,
    COUNT(DISTINCT election_id) AS elections,
    COUNT(*) AS rows
FROM marts.agent_electoral_summary
WHERE municipio_id = '29070'
GROUP BY election_type, election_year
ORDER BY election_type, election_year;

SELECT
    year,
    COUNT(*) AS rows,
    COUNT(DISTINCT section_id) AS sections,
    COUNT(*) FILTER (WHERE income_individual IS NOT NULL) AS income_individual_not_null,
    COUNT(*) FILTER (WHERE pension_share IS NOT NULL) AS pension_share_not_null
FROM marts.agent_income_sources
WHERE municipio_id = '29070'
GROUP BY year
ORDER BY year;

SELECT
    year,
    COUNT(*) AS rows,
    COUNT(DISTINCT section_id) AS sections,
    COUNT(*) FILTER (WHERE market_price_estimated_m2 IS NOT NULL) AS market_price_estimated_m2_not_null,
    COUNT(*) FILTER (WHERE residential_pressure_index IS NOT NULL) AS residential_pressure_index_not_null
FROM marts.agent_housing_profile
WHERE municipio_id = '29070'
GROUP BY year
ORDER BY year;
