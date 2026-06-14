SELECT
    municipality_id,
    COUNT(*) AS section_count,
    ARRAY_AGG(DISTINCT anio ORDER BY anio DESC) FILTER (WHERE anio IS NOT NULL) AS available_years
FROM (
    SELECT
        LEFT(vm.seccion_id, 5) AS municipality_id,
        mfp.anio
    FROM marts.v_mapa_seccion_2023 vm
    LEFT JOIN marts.mijas_features_panel mfp
      ON mfp.seccion_id = vm.seccion_id
) municipality_rows
GROUP BY municipality_id
ORDER BY municipality_id;

