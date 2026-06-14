from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


DEFAULT_INPUT = Path("data/raw/ine/29070_Mijas_Edad_2021_2025.csv")
DEFAULT_DB = "postgresql:///mijas"
POPULATION_YEARS = (2021, 2022, 2023, 2024, 2025)


RAW_DDL = """
CREATE TABLE IF NOT EXISTS raw.demografia_genero_edad_multi_anio (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    edad TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);
"""


STAGING_DDL = """
CREATE TABLE IF NOT EXISTS staging.fact_genero_edad_multi_anio (
    seccion_id TEXT,
    anio INTEGER,
    genero TEXT,
    edad_cohorte TEXT,
    poblacion INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load INE population by census section for multiple years.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--years", type=int, nargs="+", default=list(POPULATION_YEARS))
    parser.add_argument("--cod-municipio", default="29070")
    parser.add_argument("--db", default=DEFAULT_DB)
    return parser.parse_args()


def read_ine_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, sep=";", encoding=encoding, dtype=str)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Unable to read {path} with expected encodings") from last_error


def normalize_population(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip()
    if raw in {"", ".."}:
        return None
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return int(round(float(normalized)))
    except ValueError:
        return None


def extract_seccion_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"\b(\d{10})\b", str(value))
    return match.group(1) if match else None


def normalize_genero(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"hombres", "hombre", "h", "varones", "varon"}:
        return "H"
    if normalized in {"mujeres", "mujer", "m"}:
        return "M"
    if normalized in {"total", "ambos sexos", "todos"}:
        return "TOTAL"
    return None


def normalize_edad_cohorte(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )

    if normalized == "todas las edades":
        return "TOTAL"

    range_match = re.search(r"de\s+(\d+)\s+a\s+(\d+)\s+anos", normalized)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"

    plus_match = re.search(r"(\d+)\s+y\s+mas\s+anos", normalized)
    if plus_match:
        return f"{plus_match.group(1)}+"

    return str(value).strip()


def prepare_raw(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    expected = ["Provincias", "Municipios", "Secciones", "Sexo", "Edad", "Periodo", "Total"]
    missing = [column for column in expected if column not in df.columns]
    if missing:
        raise ValueError(f"Missing expected INE columns: {', '.join(missing)}")

    raw = df[expected].copy()
    raw.columns = ["provincias", "municipios", "secciones", "sexo", "edad", "periodo", "total"]
    raw["source_file"] = source_file
    return raw


def prepare_staging(raw: pd.DataFrame, years: set[int], cod_municipio: str, source_file: str) -> pd.DataFrame:
    staging = pd.DataFrame(
        {
            "seccion_id": raw["secciones"].map(extract_seccion_id),
            "anio": pd.to_numeric(raw["periodo"], errors="coerce").astype("Int64"),
            "genero": raw["sexo"].map(normalize_genero),
            "edad_cohorte": raw["edad"].map(normalize_edad_cohorte),
            "poblacion": raw["total"].map(normalize_population),
            "source_file": source_file,
        }
    )

    staging = staging[
        staging["anio"].isin(years)
        & staging["seccion_id"].str.startswith(cod_municipio, na=False)
    ].copy()
    staging = staging.dropna(subset=["seccion_id", "anio", "genero", "edad_cohorte", "poblacion"])
    staging["anio"] = staging["anio"].astype(int)
    staging["poblacion"] = staging["poblacion"].astype(int)
    return staging.drop_duplicates(subset=["seccion_id", "anio", "genero", "edad_cohorte"])


def ensure_objects(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text(RAW_DDL))
        conn.execute(text(STAGING_DDL))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS core.poblacion_edad (
                    seccion_id TEXT NOT NULL,
                    anio INTEGER NOT NULL,
                    genero TEXT NOT NULL,
                    edad_cohorte TEXT NOT NULL,
                    poblacion INTEGER NOT NULL,
                    PRIMARY KEY (seccion_id, anio, genero, edad_cohorte)
                )
                """
            )
        )


def load_raw(engine, raw: pd.DataFrame, source_file: str) -> int:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM raw.demografia_genero_edad_multi_anio WHERE source_file = :source_file"),
            {"source_file": source_file},
        )
    raw.to_sql(
        "demografia_genero_edad_multi_anio",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
    )
    return len(raw)


def load_staging(engine, staging: pd.DataFrame, years: set[int], source_file: str) -> int:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM staging.fact_genero_edad_multi_anio
                WHERE source_file = :source_file
                   OR anio = ANY(:years)
                """
            ),
            {"source_file": source_file, "years": list(years)},
        )
    staging.to_sql(
        "fact_genero_edad_multi_anio",
        engine,
        schema="staging",
        if_exists="append",
        index=False,
    )
    return len(staging)


def upsert_core(engine, years: set[int]) -> int:
    upsert_sql = """
    INSERT INTO core.poblacion_edad (
        seccion_id,
        anio,
        genero,
        edad_cohorte,
        poblacion
    )
    SELECT
        seccion_id,
        anio,
        genero,
        edad_cohorte,
        poblacion
    FROM staging.fact_genero_edad_multi_anio
    WHERE genero IN ('H', 'M')
      AND edad_cohorte <> 'TOTAL'
      AND anio = ANY(:years)
    ON CONFLICT (seccion_id, anio, genero, edad_cohorte)
    DO UPDATE SET poblacion = EXCLUDED.poblacion;
    """
    with engine.begin() as conn:
        result = conn.execute(text(upsert_sql), {"years": list(years)})
    return result.rowcount or 0


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(args.input)

    years = set(args.years)
    engine = create_engine(args.db)
    ensure_objects(engine)

    source_file = args.input.name
    df = read_ine_csv(args.input)
    raw = prepare_raw(df, source_file)
    staging = prepare_staging(raw, years, args.cod_municipio, source_file)

    raw_rows = load_raw(engine, raw, source_file)
    staging_rows = load_staging(engine, staging, years, source_file)
    core_rows = upsert_core(engine, years)

    print("Population multi-year load completed")
    print(f"- source file: {source_file}")
    print(f"- raw rows loaded: {raw_rows}")
    print(f"- staging rows loaded for Mijas/years: {staging_rows}")
    print(f"- core rows inserted/updated: {core_rows}")
    print("- sections by year:")
    sections_by_year = (
        staging[staging["genero"].isin(["H", "M"])]
        .groupby("anio")["seccion_id"]
        .nunique()
        .sort_index()
    )
    for year, count in sections_by_year.items():
        print(f"  - {year}: {count}")


if __name__ == "__main__":
    main()
