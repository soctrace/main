from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import create_engine, text


DEFAULT_INPUT = Path("data/raw/geografia/seccionado_2019.zip")
DEFAULT_DB = "postgresql:///mijas"
GIS_SUFFIXES = {".shp", ".gpkg", ".geojson", ".json", ".gml"}

COLUMN_CANDIDATES = {
    "cusec": ("CUSEC", "CUSECSEC", "CSEC_CUSEC", "SECCION_ID", "seccion_id"),
    "cod_provincia": ("CPRO", "COD_PROV", "CODPROV", "PROV", "cod_provincia"),
    "cod_municipio": ("CMUN", "COD_MUN", "CODMUN", "MUN", "cod_municipio"),
    "cod_distrito": ("CDIS", "CDIST", "COD_DIST", "CODDISTRIT", "cod_distrito"),
    "cod_seccion": ("CSEC", "CSECC", "COD_SEC", "CODSECC", "cod_seccion"),
}


DDL_SQL = """
CREATE TABLE IF NOT EXISTS core.seccion_historica (
    seccion_sk BIGSERIAL PRIMARY KEY,
    seccion_id TEXT NOT NULL,
    anio INT NOT NULL,

    cod_provincia CHAR(2) NOT NULL,
    cod_municipio CHAR(3) NOT NULL,
    cod_distrito CHAR(2) NOT NULL,
    cod_seccion CHAR(3) NOT NULL,

    geom geometry(MultiPolygon, 4326) NOT NULL,

    area_m2 NUMERIC,
    area_km2 NUMERIC,

    source_file TEXT,
    source_layer TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (seccion_id, anio)
);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_anio
    ON core.seccion_historica (anio);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_seccion_anio
    ON core.seccion_historica (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_geom
    ON core.seccion_historica
    USING GIST (geom);
"""


VIEW_SQL_TEMPLATE = """
CREATE OR REPLACE VIEW marts.v_mapa_seccion_{anio} AS
SELECT
    h.seccion_id,
    h.anio,
    COALESCE(d.seccion_numero_visible, RIGHT(h.seccion_id, 3)) AS seccion_numero_visible,
    d.nombre_barrio,
    d.zona_macro,
    COALESCE(d.label_cliente, 'Mijas - Section ' || RIGHT(h.seccion_id, 3)) AS label_cliente,
    h.area_m2,
    h.area_km2,
    h.geom,
    ST_AsGeoJSON(h.geom)::json AS geom_json
FROM core.seccion_historica h
LEFT JOIN marts.dim_seccion_display d
  ON h.seccion_id = d.seccion_id
WHERE h.anio = {anio};
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load historical census sections into core.seccion_historica."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--anio", type=int, default=2019)
    parser.add_argument("--years", type=int, nargs="+", default=None)
    parser.add_argument("--cod-provincia", default="29")
    parser.add_argument("--cod-municipio", default="070")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=None,
        help="Optional controlled extraction directory for ZIP inputs.",
    )
    return parser.parse_args()


def normalize_digits(value: object, width: int) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    return digits.zfill(width)[-width:]


def find_column(columns: list[str], logical_name: str) -> str | None:
    upper_map = {column.upper(): column for column in columns}
    for candidate in COLUMN_CANDIDATES[logical_name]:
        match = upper_map.get(candidate.upper())
        if match:
            return match
    return None


def extract_if_needed(input_path: Path, extract_dir: Path | None) -> Path:
    if input_path.suffix.lower() != ".zip":
        return input_path

    target_dir = extract_dir or input_path.with_suffix("")
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(input_path) as archive:
        archive.extractall(target_dir)

    return target_dir


def detect_geospatial_file(path: Path) -> Path:
    if path.is_file() and path.suffix.lower() in GIS_SUFFIXES:
        return path

    if not path.is_dir():
        raise FileNotFoundError(f"No supported GIS input found at {path}")

    candidates = [
        file
        for file in path.rglob("*")
        if file.is_file() and file.suffix.lower() in GIS_SUFFIXES
    ]
    if not candidates:
        raise FileNotFoundError(f"No supported GIS file found inside {path}")

    priority = {".shp": 0, ".gpkg": 1, ".geojson": 2, ".json": 3, ".gml": 4}
    return sorted(candidates, key=lambda file: (priority[file.suffix.lower()], str(file)))[0]


def detect_year_input(input_dir: Path, year: int) -> Path:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    year_text = str(year)
    candidates = [
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and year_text in path.stem
        and (path.suffix.lower() == ".zip" or path.suffix.lower() in GIS_SUFFIXES)
    ]
    if not candidates:
        candidates = [
            path
            for path in input_dir.iterdir()
            if path.is_dir() and year_text in path.name
        ]

    if not candidates:
        raise FileNotFoundError(f"No GIS ZIP/file found for year {year} in {input_dir}")

    return sorted(candidates, key=lambda path: str(path))[0]


def to_multipolygon(geom):
    if geom is None or geom.is_empty:
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    if geom.geom_type == "GeometryCollection":
        polygons = [part for part in geom.geoms if isinstance(part, Polygon)]
        return MultiPolygon(polygons) if polygons else None
    return geom


def normalize_sections(
    gdf: gpd.GeoDataFrame,
    anio: int,
    cod_provincia: str,
    cod_municipio: str,
    source_file: str,
    source_layer: str,
) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError("Input geospatial file has no CRS. Cannot safely reproject.")

    columns = list(gdf.columns)
    cusec_col = find_column(columns, "cusec")
    prov_col = find_column(columns, "cod_provincia")
    mun_col = find_column(columns, "cod_municipio")
    dist_col = find_column(columns, "cod_distrito")
    sec_col = find_column(columns, "cod_seccion")

    if cusec_col:
        cusec = gdf[cusec_col].map(lambda value: normalize_digits(value, 10))
        gdf = gdf.assign(
            seccion_id=cusec,
            cod_provincia=cusec.str.slice(0, 2),
            cod_municipio=cusec.str.slice(2, 5),
            cod_distrito=cusec.str.slice(5, 7),
            cod_seccion=cusec.str.slice(7, 10),
        )
    else:
        missing = [
            name
            for name, column in {
                "cod_provincia": prov_col,
                "cod_municipio": mun_col,
                "cod_distrito": dist_col,
                "cod_seccion": sec_col,
            }.items()
            if column is None
        ]
        if missing:
            raise ValueError(f"Missing required code columns: {', '.join(missing)}")

        gdf = gdf.assign(
            cod_provincia=gdf[prov_col].map(lambda value: normalize_digits(value, 2)),
            cod_municipio=gdf[mun_col].map(lambda value: normalize_digits(value, 3)),
            cod_distrito=gdf[dist_col].map(lambda value: normalize_digits(value, 2)),
            cod_seccion=gdf[sec_col].map(lambda value: normalize_digits(value, 3)),
        )
        gdf["seccion_id"] = (
            gdf["cod_provincia"]
            + gdf["cod_municipio"]
            + gdf["cod_distrito"]
            + gdf["cod_seccion"]
        )

    target_prov = normalize_digits(cod_provincia, 2)
    target_mun = normalize_digits(cod_municipio, 3)
    filtered = gdf[
        (gdf["cod_provincia"] == target_prov)
        & (gdf["cod_municipio"] == target_mun)
    ].copy()

    if filtered.empty:
        raise ValueError(f"No features found for province={target_prov}, municipality={target_mun}")

    filtered = filtered.to_crs(epsg=4326)
    filtered["geometry"] = filtered.geometry.apply(to_multipolygon)
    filtered = filtered.dropna(subset=["geometry"])
    filtered = filtered[~filtered.geometry.is_empty].copy()
    filtered = filtered.set_geometry("geometry")

    area_gdf = filtered.to_crs(epsg=25830)
    filtered["area_m2"] = area_gdf.geometry.area
    filtered["area_km2"] = filtered["area_m2"] / 1_000_000
    filtered["anio"] = anio
    filtered["source_file"] = source_file
    filtered["source_layer"] = source_layer

    keep_cols = [
        "seccion_id",
        "anio",
        "cod_provincia",
        "cod_municipio",
        "cod_distrito",
        "cod_seccion",
        "area_m2",
        "area_km2",
        "source_file",
        "source_layer",
        "geometry",
    ]
    filtered = filtered[keep_cols].drop_duplicates(subset=["seccion_id", "anio"])
    return filtered


def ensure_database_objects(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts"))
        for statement in DDL_SQL.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.execute(text(
            "COMMENT ON TABLE core.seccion_historica IS "
            "'Historical census/electoral sections by year. Does not replace core.seccion, "
            "which remains the current operative geography.'"
        ))


def create_map_view(engine, anio: int) -> None:
    if anio == 2023:
        return
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL_TEMPLATE.format(anio=int(anio))))


def upsert_sections(engine, gdf: gpd.GeoDataFrame) -> int:
    temp_table = "seccion_historica_load_tmp"

    with tempfile.TemporaryDirectory():
        gdf.to_postgis(
            temp_table,
            engine,
            schema="staging",
            if_exists="replace",
            index=False,
        )

        upsert_sql = f"""
        INSERT INTO core.seccion_historica (
            seccion_id,
            anio,
            cod_provincia,
            cod_municipio,
            cod_distrito,
            cod_seccion,
            geom,
            area_m2,
            area_km2,
            source_file,
            source_layer,
            loaded_at
        )
        SELECT
            seccion_id,
            anio,
            cod_provincia,
            cod_municipio,
            cod_distrito,
            cod_seccion,
            ST_Multi(ST_CollectionExtract(ST_MakeValid(geometry), 3))::geometry(MultiPolygon, 4326),
            area_m2,
            area_km2,
            source_file,
            source_layer,
            NOW()
        FROM staging.{temp_table}
        ON CONFLICT (seccion_id, anio)
        DO UPDATE SET
            geom = EXCLUDED.geom,
            area_m2 = EXCLUDED.area_m2,
            area_km2 = EXCLUDED.area_km2,
            source_file = EXCLUDED.source_file,
            source_layer = EXCLUDED.source_layer,
            loaded_at = NOW();
        """

        with engine.begin() as conn:
            result = conn.execute(text(upsert_sql))
            conn.execute(text(f"DROP TABLE IF EXISTS staging.{temp_table}"))

    return result.rowcount or len(gdf)


def load_year(
    engine,
    input_path: Path,
    anio: int,
    cod_provincia: str,
    cod_municipio: str,
    extract_dir: Path | None,
) -> dict[str, object]:
    extracted_path = extract_if_needed(input_path, extract_dir)
    gis_file = detect_geospatial_file(extracted_path)

    print(f"Reading {anio}: {gis_file}")
    source_layer = gis_file.stem
    gdf = gpd.read_file(gis_file)
    total_features = len(gdf)

    normalized = normalize_sections(
        gdf,
        anio=anio,
        cod_provincia=cod_provincia,
        cod_municipio=cod_municipio,
        source_file=input_path.name,
        source_layer=source_layer,
    )

    affected_rows = upsert_sections(engine, normalized)
    create_map_view(engine, anio)

    summary = {
        "year": anio,
        "source_file": input_path.name,
        "gis_file": str(gis_file),
        "features_read": total_features,
        "mijas_sections": len(normalized),
        "srid": 4326,
        "affected_rows": affected_rows,
        "min_seccion_id": normalized["seccion_id"].min(),
        "max_seccion_id": normalized["seccion_id"].max(),
        "min_area_km2": float(normalized["area_km2"].min()),
        "max_area_km2": float(normalized["area_km2"].max()),
    }
    print_year_summary(summary)
    return summary


def print_year_summary(summary: dict[str, object]) -> None:
    print(f"Load completed for {summary['year']}")
    print(f"- source file: {summary['source_file']}")
    print(f"- features read: {summary['features_read']}")
    print(f"- Mijas sections filtered: {summary['mijas_sections']}")
    print(f"- final SRID: {summary['srid']}")
    print(f"- inserted/updated rows: {summary['affected_rows']}")
    print(f"- seccion_id range: {summary['min_seccion_id']} - {summary['max_seccion_id']}")
    print(
        "- area_km2 min/max: "
        f"{summary['min_area_km2']:.6f} / {summary['max_area_km2']:.6f}"
    )


def main() -> None:
    args = parse_args()
    engine = create_engine(args.db)
    ensure_database_objects(engine)

    years = args.years or [args.anio]
    summaries = []

    for year in years:
        input_path = detect_year_input(args.input_dir, year) if args.input_dir else args.input
        extract_dir = args.extract_dir
        if args.input_dir and extract_dir is not None:
            extract_dir = extract_dir / str(year)
        summaries.append(
            load_year(
                engine=engine,
                input_path=input_path,
                anio=year,
                cod_provincia=args.cod_provincia,
                cod_municipio=args.cod_municipio,
                extract_dir=extract_dir,
            )
        )

    if len(summaries) > 1:
        print("\nMulti-year load summary")
        for summary in summaries:
            print(
                f"- {summary['year']}: {summary['mijas_sections']} sections, "
                f"{summary['min_seccion_id']} - {summary['max_seccion_id']}, "
                f"source={summary['source_file']}"
            )


if __name__ == "__main__":
    main()
