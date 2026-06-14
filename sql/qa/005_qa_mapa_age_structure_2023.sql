SELECT
    COUNT(*) AS n_sections,
    COUNT(*) FILTER (WHERE average_age IS NULL) AS missing_average_age,
    COUNT(*) FILTER (WHERE over_65_pct IS NULL) AS missing_over_65_pct,
    COUNT(*) FILTER (WHERE under_30_pct IS NULL) AS missing_under_30_pct,
    COUNT(*) FILTER (WHERE density_level IS NULL) AS missing_density_level,
    COUNT(DISTINCT age_group) AS n_age_groups,
    MIN(average_age) AS min_average_age,
    MAX(average_age) AS max_average_age
FROM marts.v_mapa_age_structure_2023;

SELECT
    age_group,
    age_group_label,
    age_color_key,
    COUNT(*) AS n_sections
FROM marts.v_mapa_age_structure_2023
GROUP BY age_group, age_group_label, age_color_key
ORDER BY age_group;

SELECT
    density_level,
    COUNT(*) AS n_sections
FROM marts.v_mapa_age_structure_2023
GROUP BY density_level
ORDER BY MIN(densidad);
