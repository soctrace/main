DROP VIEW IF EXISTS marts.v_land_built_environment CASCADE;

CREATE VIEW marts.v_land_built_environment AS
/*
Land / Built Environment physical occupation layer.

Urban Intensity is a 0-100 composite index of observable physical urban
occupation. It is not a housing-market pressure, price, demand, gentrification
or valuation signal.
*/
WITH base AS (
    SELECT
        ti.seccion_id,
        ti.anio,
        ti.seccion_numero_visible,
        ti.nombre_barrio,
        ti.zona_macro,
        ti.label_cliente,
        ti.geom,
        ST_AsGeoJSON(ST_Transform(ST_Force2D(ti.geom), 4326))::json AS geom_json,
        ti.pob_total,
        ti.densidad,
        ti.num_parcelas,
        ti.superficie_total_parcelas_m2,
        ti.superficie_media_parcela_m2,
        CASE
            WHEN mfp.area_km2 > 0 THEN ti.num_parcelas::numeric / mfp.area_km2::numeric
            ELSE NULL::numeric
        END AS densidad_parcelaria,
        ti.num_building_parts,
        ti.huella_construida_m2,
        ti.huella_media_building_part_m2,
        ti.indice_construido
    FROM marts.territorial_intelligence_section_2023 ti
    LEFT JOIN marts.mijas_features_panel mfp
      ON mfp.seccion_id = ti.seccion_id
     AND mfp.anio = ti.anio
),
stats AS (
    SELECT
        anio,
        MIN(densidad) AS density_min,
        MAX(densidad) AS density_max,
        MIN(indice_construido) AS built_intensity_min,
        MAX(indice_construido) AS built_intensity_max,
        MIN(densidad_parcelaria) AS parcel_density_min,
        MAX(densidad_parcelaria) AS parcel_density_max,
        MIN(superficie_media_parcela_m2) AS avg_plot_size_min,
        MAX(superficie_media_parcela_m2) AS avg_plot_size_max
    FROM base
    GROUP BY anio
),
normalized AS (
    SELECT
        b.*,
        CASE
            WHEN s.density_max > s.density_min THEN
                100 * (b.densidad - s.density_min) / NULLIF(s.density_max - s.density_min, 0)
            ELSE NULL::numeric
        END AS density_norm,
        CASE
            WHEN s.built_intensity_max > s.built_intensity_min THEN
                100 * (b.indice_construido - s.built_intensity_min) / NULLIF(s.built_intensity_max - s.built_intensity_min, 0)
            ELSE NULL::numeric
        END AS built_intensity_norm,
        CASE
            WHEN s.parcel_density_max > s.parcel_density_min THEN
                100 * (b.densidad_parcelaria - s.parcel_density_min) / NULLIF(s.parcel_density_max - s.parcel_density_min, 0)
            ELSE NULL::numeric
        END AS parcel_density_norm,
        CASE
            WHEN s.avg_plot_size_max > s.avg_plot_size_min THEN
                100 - (100 * (b.superficie_media_parcela_m2 - s.avg_plot_size_min) / NULLIF(s.avg_plot_size_max - s.avg_plot_size_min, 0))
            ELSE NULL::numeric
        END AS inverse_plot_size_norm
    FROM base b
    JOIN stats s
      ON s.anio = b.anio
),
weighted AS (
    SELECT
        *,
        (CASE WHEN density_norm IS NOT NULL THEN 0.35 ELSE 0 END
         + CASE WHEN built_intensity_norm IS NOT NULL THEN 0.35 ELSE 0 END
         + CASE WHEN parcel_density_norm IS NOT NULL THEN 0.20 ELSE 0 END
         + CASE WHEN inverse_plot_size_norm IS NOT NULL THEN 0.10 ELSE 0 END) AS available_weight,
        (CASE WHEN density_norm IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN built_intensity_norm IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN parcel_density_norm IS NOT NULL THEN 1 ELSE 0 END
         + CASE WHEN inverse_plot_size_norm IS NOT NULL THEN 1 ELSE 0 END) AS available_variables
    FROM normalized
)
SELECT
    seccion_id,
    anio,
    geom,
    geom_json,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    pob_total,
    densidad,
    num_parcelas,
    superficie_total_parcelas_m2,
    superficie_media_parcela_m2,
    densidad_parcelaria,
    num_building_parts,
    huella_construida_m2,
    huella_media_building_part_m2,
    indice_construido,
    ROUND(LEAST(100, GREATEST(0, density_norm))::numeric, 2) AS density_norm,
    ROUND(LEAST(100, GREATEST(0, built_intensity_norm))::numeric, 2) AS built_intensity_norm,
    ROUND(LEAST(100, GREATEST(0, parcel_density_norm))::numeric, 2) AS parcel_density_norm,
    ROUND(LEAST(100, GREATEST(0, inverse_plot_size_norm))::numeric, 2) AS inverse_plot_size_norm,
    ROUND(
        CASE
            WHEN available_weight > 0 THEN LEAST(100, GREATEST(0,
                (
                    COALESCE(0.35 * density_norm, 0)
                    + COALESCE(0.35 * built_intensity_norm, 0)
                    + COALESCE(0.20 * parcel_density_norm, 0)
                    + COALESCE(0.10 * inverse_plot_size_norm, 0)
                ) / available_weight
            ))
            ELSE NULL::numeric
        END,
        2
    ) AS urban_intensity_index,
    CASE
        WHEN available_weight <= 0 THEN NULL
        WHEN (
            COALESCE(0.35 * density_norm, 0)
            + COALESCE(0.35 * built_intensity_norm, 0)
            + COALESCE(0.20 * parcel_density_norm, 0)
            + COALESCE(0.10 * inverse_plot_size_norm, 0)
        ) / available_weight < 20 THEN 'Very Low'
        WHEN (
            COALESCE(0.35 * density_norm, 0)
            + COALESCE(0.35 * built_intensity_norm, 0)
            + COALESCE(0.20 * parcel_density_norm, 0)
            + COALESCE(0.10 * inverse_plot_size_norm, 0)
        ) / available_weight < 40 THEN 'Low'
        WHEN (
            COALESCE(0.35 * density_norm, 0)
            + COALESCE(0.35 * built_intensity_norm, 0)
            + COALESCE(0.20 * parcel_density_norm, 0)
            + COALESCE(0.10 * inverse_plot_size_norm, 0)
        ) / available_weight < 60 THEN 'Medium'
        WHEN (
            COALESCE(0.35 * density_norm, 0)
            + COALESCE(0.35 * built_intensity_norm, 0)
            + COALESCE(0.20 * parcel_density_norm, 0)
            + COALESCE(0.10 * inverse_plot_size_norm, 0)
        ) / available_weight < 80 THEN 'High'
        ELSE 'Very High'
    END AS urban_intensity_label,
    ROUND((available_variables * 100.0 / 4)::numeric, 2) AS urban_intensity_completeness_pct
FROM weighted;

COMMENT ON VIEW marts.v_land_built_environment IS
    'Land / Built Environment physical occupation mart. urban_intensity_index is a 0-100 composite index based on population density, built intensity, parcel density and inverse average plot size.';
