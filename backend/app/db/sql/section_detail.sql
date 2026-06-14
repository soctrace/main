WITH base_sections AS (
    SELECT
        vm.seccion_id,
        vm.anio,
        vm.seccion_numero_visible,
        vm.nombre_barrio,
        vm.zona_macro,
        vm.label_cliente,
        vm.geom
    FROM marts.v_mapa_seccion_anio vm
    WHERE vm.anio = :year
)
SELECT
    bs.seccion_id,
    bs.seccion_numero_visible,
    bs.nombre_barrio,
    bs.zona_macro,
    bs.label_cliente,
    SUBSTRING(bs.seccion_id FROM 1 FOR 5) AS municipality_id,
    SUBSTRING(bs.seccion_id FROM 6 FOR 2) AS district_code,
    ST_Area(bs.geom::geography) / 1000000.0 AS area_km2_geodesic,
    COALESCE(mfp.anio, bs.anio) AS anio,
    COALESCE(mfp.election_id, r.election_id) AS election_id,
    COALESCE(pop.densidad, mfp.densidad) AS densidad,
    COALESCE(pop.pob_total, mfp.pob_total) AS pob_total,
    COALESCE(pop.pob_h, mfp.pob_h) AS pob_h,
    COALESCE(pop.pob_m, mfp.pob_m) AS pob_m,
    COALESCE(pop.pob_0_14, mfp.pob_0_14) AS pob_0_14,
    COALESCE(pop.pob_15_29, mfp.pob_15_29) AS pob_15_29,
    COALESCE(pop.pob_30_44, mfp.pob_30_44) AS pob_30_44,
    COALESCE(pop.pob_45_64, mfp.pob_45_64) AS pob_45_64,
    COALESCE(pop.pob_65p, mfp.pob_65p) AS pob_65p,
    COALESCE(pop.pct_0_14, mfp.pct_0_14) AS pct_0_14,
    COALESCE(pop.pct_15_29, mfp.pct_15_29) AS pct_15_29,
    COALESCE(pop.pct_30_44, mfp.pct_30_44) AS pct_30_44,
    COALESCE(pop.pct_45_64, mfp.pct_45_64) AS pct_45_64,
    COALESCE(pop.pct_65p, mfp.pct_65p) AS pct_65p,
    COALESCE(pop.dependency_ratio, mfp.dependency_ratio) AS dependency_ratio,
    r.censo,
    r.votos_emitidos,
    r.votos_validos,
    r.votos_blanco,
    r.votos_nulos,
    r.participacion,
    r.blanco_pct,
    r.nulos_pct,
    COALESCE(eb.winning_party, r.sigla_ganadora) AS sigla_ganadora,
    r.pct_pp,
    r.pct_psoe,
    r.pct_vox,
    COALESCE(il.renta_media_persona, mfp.renta_media_persona) AS renta_media_persona,
    COALESCE(il.renta_media_hogar, mfp.renta_media_hogar) AS renta_media_hogar,
    COALESCE(il.income_quintile, mfp.income_quintile) AS income_quintile,
    COALESCE(il.income_level, mfp.income_level) AS income_level,
    COALESCE(il.income_rank_municipal, mfp.income_rank_municipal) AS income_rank_municipal,
    COALESCE(il.income_index, mfp.income_index) AS income_index,
    isp.income_salary,
    isp.income_pension,
    isp.income_unemployment,
    isp.income_social_benefits,
    isp.income_other,
    isp.pension_dependency_index,
    isp.employment_dependency_index,
    isp.welfare_dependency_index,
    isp.entrepreneurial_activity_signal,
    isp.passive_income_signal
FROM base_sections bs
LEFT JOIN marts.v_population_layer pop
  ON pop.seccion_id = bs.seccion_id
 AND pop.anio = bs.anio
LEFT JOIN marts.mijas_features_panel mfp
  ON mfp.seccion_id = bs.seccion_id
 AND mfp.anio = :year
LEFT JOIN marts.v_income_level il
  ON il.seccion_id = bs.seccion_id
 AND il.anio = :year
LEFT JOIN marts.v_income_sources_profile isp
  ON isp.seccion_id = bs.seccion_id
 AND isp.anio = :year
LEFT JOIN marts.v_resultados_seccion_anio r
  ON r.seccion_id = bs.seccion_id
 AND r.anio = :year
 AND (CAST(:election_id AS bigint) IS NULL OR r.election_id = CAST(:election_id AS bigint))
LEFT JOIN marts.mv_electoral_behavior eb
  ON eb.seccion_id = bs.seccion_id
 AND eb.anio = :year
 AND eb.election_id = r.election_id
WHERE bs.seccion_id = :section_id
ORDER BY COALESCE(r.election_id, mfp.election_id) DESC NULLS LAST
LIMIT 1;
