from __future__ import annotations

import argparse
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from etl.common.db import get_engine
from etl.common.io import read_csv_safe
from etl.common.logging_utils import get_logger


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = (
    PROJECT_ROOT / "data" / "raw" / "ine" / "29070_Mijas_RentaMedia_Individual_Hogar_2019_2023.csv"
)
FUENTE = "INE - Atlas de Distribución de Renta"
YEARS = (2019, 2020, 2021, 2022, 2023)

DDL_FILES = [
    PROJECT_ROOT / "sql" / "raw" / "005_create_raw_renta_ine_2019_2023.sql",
    PROJECT_ROOT / "sql" / "staging" / "006_create_staging_renta_seccion_multi_anio.sql",
    PROJECT_ROOT / "sql" / "core" / "002_create_core_renta_seccion.sql",
    PROJECT_ROOT / "sql" / "marts" / "011_v_income_level.sql",
]


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_column_name(value: str) -> str:
    value = strip_accents(value).strip().lower()
    value = value.replace(" ", "_").replace("__", "_")

    if value == "indicadores_de_renta_media_y_mediana":
        return "indicador"

    return value


def extract_seccion_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None

    match = re.search(r"\b(\d{10})\b", str(value))
    return match.group(1) if match else None


def normalize_indicador(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None

    normalized = strip_accents(str(value)).strip().lower()

    if "renta neta media" in normalized and "persona" in normalized:
        return "renta_media_persona"
    if "renta neta media" in normalized and "hogar" in normalized:
        return "renta_media_hogar"

    return None


def parse_ine_number(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None

    raw = str(value).strip()
    if raw in {"", ".."}:
        return None

    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    else:
        # INE Spanish thousands separator: 11.333 means 11333 euros.
        normalized = raw.replace(".", "")

    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"No se pudo convertir Total='{value}' a número INE") from exc


def run_sql_file(conn, path: Path) -> None:
    logger.info("Ejecutando SQL: %s", path.relative_to(PROJECT_ROOT))
    conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def prepare_raw(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
    expected_columns = ["municipios", "distritos", "secciones", "indicador", "periodo", "total"]
    missing_columns = [column for column in expected_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas esperadas: {missing_columns}")

    raw = df[expected_columns].copy()
    raw["source_file"] = source_file
    return raw


def prepare_staging(raw: pd.DataFrame, source_file: str) -> pd.DataFrame:
    staging = pd.DataFrame(
        {
            "seccion_id": raw["secciones"].apply(extract_seccion_id),
            "anio": pd.to_numeric(raw["periodo"], errors="coerce").astype("Int64"),
            "indicador_norm": raw["indicador"].apply(normalize_indicador),
            "valor": raw["total"].apply(parse_ine_number),
            "source_file": source_file,
        }
    )
    staging = staging[staging["anio"].isin(YEARS)].copy()
    staging = staging.dropna(subset=["seccion_id", "anio", "indicador_norm", "valor"])
    staging["anio"] = staging["anio"].astype(int)

    bad_section_ids = staging.loc[~staging["seccion_id"].str.match(r"^\d{10}$"), "seccion_id"].unique()
    if len(bad_section_ids) > 0:
        raise ValueError(f"seccion_id no válidos: {bad_section_ids.tolist()}")

    duplicates = staging.duplicated(subset=["seccion_id", "anio", "indicador_norm"], keep=False)
    if duplicates.any():
        duplicated_rows = staging.loc[duplicates, ["seccion_id", "anio", "indicador_norm"]]
        raise ValueError(f"Duplicados en staging: {duplicated_rows.drop_duplicates().to_dict('records')}")

    return staging


def load_renta_ine_multi_year(csv_path: str | Path = DEFAULT_CSV_PATH) -> None:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    source_file = path.name
    logger.info("Leyendo CSV INE renta multi-año: %s", path)
    raw = prepare_raw(read_csv_safe(path, dtype=str), source_file)
    staging = prepare_staging(raw, source_file)

    expected_rows = len(YEARS) * 37 * 2
    if len(staging) != expected_rows:
        logger.warning("Filas staging esperadas %s, detectadas %s", expected_rows, len(staging))

    engine = get_engine()
    with engine.begin() as conn:
        for ddl_file in DDL_FILES:
            run_sql_file(conn, ddl_file)

        logger.info("Limpiando raw/staging para source_file=%s ...", source_file)
        conn.execute(
            text("DELETE FROM raw.renta_ine_2019_2023 WHERE source_file = :source_file"),
            {"source_file": source_file},
        )
        conn.execute(
            text(
                """
                DELETE FROM staging.renta_seccion_multi_anio
                WHERE source_file = :source_file
                   OR anio = ANY(:years)
                """
            ),
            {"source_file": source_file, "years": list(YEARS)},
        )

    logger.info("Insertando %s filas en raw.renta_ine_2019_2023 ...", len(raw))
    raw.to_sql(
        name="renta_ine_2019_2023",
        con=engine,
        schema="raw",
        if_exists="append",
        index=False,
    )

    logger.info("Insertando %s filas en staging.renta_seccion_multi_anio ...", len(staging))
    staging.to_sql(
        name="renta_seccion_multi_anio",
        con=engine,
        schema="staging",
        if_exists="append",
        index=False,
    )

    upsert_sql = text(
        """
        INSERT INTO core.renta_seccion (
            seccion_id,
            anio,
            renta_media_persona,
            renta_media_hogar,
            fuente,
            updated_at
        )
        SELECT
            seccion_id,
            anio,
            MAX(CASE WHEN indicador_norm = 'renta_media_persona' THEN valor END),
            MAX(CASE WHEN indicador_norm = 'renta_media_hogar' THEN valor END),
            :fuente,
            NOW()
        FROM staging.renta_seccion_multi_anio
        WHERE anio = ANY(:years)
        GROUP BY seccion_id, anio
        ON CONFLICT (seccion_id, anio)
        DO UPDATE SET
            renta_media_persona = EXCLUDED.renta_media_persona,
            renta_media_hogar = EXCLUDED.renta_media_hogar,
            fuente = EXCLUDED.fuente,
            updated_at = NOW();
        """
    )

    with engine.begin() as conn:
        logger.info("Upsert en core.renta_seccion ...")
        result = conn.execute(upsert_sql, {"fuente": FUENTE, "years": list(YEARS)})
        logger.info("Filas insertadas/actualizadas en core: %s", result.rowcount)
        run_sql_file(conn, PROJECT_ROOT / "sql" / "marts" / "011_v_income_level.sql")

        summary = conn.execute(
            text(
                """
                SELECT
                    anio,
                    COUNT(*) AS secciones,
                    MIN(renta_media_persona) AS min_persona,
                    MAX(renta_media_persona) AS max_persona,
                    MIN(renta_media_hogar) AS min_hogar,
                    MAX(renta_media_hogar) AS max_hogar
                FROM core.renta_seccion
                WHERE anio = ANY(:years)
                GROUP BY anio
                ORDER BY anio;
                """
            ),
            {"years": list(YEARS)},
        ).mappings().all()

    for row in summary:
        logger.info(
            "Renta %s: %s secciones, persona %s-%s, hogar %s-%s",
            row["anio"],
            row["secciones"],
            row["min_persona"],
            row["max_persona"],
            row["min_hogar"],
            row["max_hogar"],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Ruta al CSV multi-año del INE de renta por sección censal",
    )
    args = parser.parse_args()

    load_renta_ine_multi_year(args.csv_path)
