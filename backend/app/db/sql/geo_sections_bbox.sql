WITH base_sections AS (
    SELECT seccion_id, geom
    FROM marts.v_mapa_seccion_anio
    WHERE anio = :year
)
SELECT
    ST_XMin(extent) AS min_lon,
    ST_YMin(extent) AS min_lat,
    ST_XMax(extent) AS max_lon,
    ST_YMax(extent) AS max_lat
FROM (
    SELECT ST_Extent(geom) AS extent
    FROM base_sections
    WHERE LEFT(seccion_id, 5) = :municipality_id
) bounds;
