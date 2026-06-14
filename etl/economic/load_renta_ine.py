from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import unicodedata

import pandas as pd
from sqlalchemy import text

from etl.common.db import get_engine
from etl.common.io import read_csv_safe
from etl.common.logging_utils import get_logger


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "ine" / "31106 (1).csv"
FUENTE = "INE - Atlas de Distribución de Renta de los Hogares"


DDL_FILES = [
    PROJECT_ROOT / "sql" / "raw" / "002_create_raw_renta_ine_2023.sql",
    PROJECT_ROOT / "sql" / "staging" / "002_create_staging_renta_seccion_2023.sql",
    PROJECT_ROOT / "sql" / "core" / "002_create_core_renta_seccion.sql",
    PROJECT_ROOT / "sql" / "marts" / "011_v_income_level.sql",
]

FEATURE_PANEL_FILES = [
    PROJECT_ROOT / "sql" / "marts" / "003_mijas_features_panel.sql",
    PROJECT_ROOT / "sql" / "marts" / "004_mijas_features_panel_indexes.sql",
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


def extract_seccion_id(value: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().split()[0]


def normalize_indicador(value: str) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = strip_accents(value).strip().lower()

    if "renta neta media" in normalized and "persona" in normalized:
        return "renta_media_persona"
    if "renta neta media" in normalized and "hogar" in normalized:
        return "renta_media_hogar"

    return None


def parse_ine_number(value: object) -> Decimal | None:
    if pd.isna(value):
        return None

    raw = str(value).strip()
    if not raw:
        return None

    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    else:
        normalized = raw.replace(".", "")

    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"No se pudo convertir Total='{value}' a número INE") from exc


def run_sql_file(conn, path: Path) -> None:
    logger.info("Ejecutando SQL: %s", path.relative_to(PROJECT_ROOT))
    conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def load_renta_ine(csv_path: str | Path = DEFAULT_CSV_PATH, refresh_features_panel: bool = False) -> None:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    logger.info("Leyendo CSV INE renta: %s", path)
    df_raw = read_csv_safe(path, dtype=str)
    df_raw.columns = [normalize_column_name(c) for c in df_raw.columns]

    expected_columns = ["municipios", "distritos", "secciones", "indicador", "periodo", "total"]
    missing_columns = [c for c in expected_columns if c not in df_raw.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas esperadas: {missing_columns}")

    df_raw = df_raw[expected_columns].copy()
    n_rows = len(df_raw)
    n_sections = df_raw["secciones"].apply(extract_seccion_id).nunique()

    if n_rows != 74:
        raise ValueError(f"Se esperaban 74 filas y se han leído {n_rows}")
    if n_sections != 37:
        raise ValueError(f"Se esperaban 37 secciones y se han detectado {n_sections}")

    df_staging = pd.DataFrame(
        {
            "seccion_id": df_raw["secciones"].apply(extract_seccion_id),
            "anio": pd.to_numeric(df_raw["periodo"], errors="raise").astype(int),
            "indicador": df_raw["indicador"].apply(normalize_indicador),
            "valor": df_raw["total"].apply(parse_ine_number),
            "fuente": FUENTE,
        }
    )

    if df_staging["indicador"].isna().any():
        bad_indicators = df_raw.loc[df_staging["indicador"].isna(), "indicador"].unique().tolist()
        raise ValueError(f"Indicadores no reconocidos: {bad_indicators}")

    if df_staging["valor"].isna().any():
        raise ValueError("Hay valores Total nulos o no convertibles en staging")

    engine = get_engine()
    with engine.begin() as conn:
        for ddl_file in DDL_FILES:
            run_sql_file(conn, ddl_file)

        logger.info("Vaciando raw.renta_ine_2023 y staging.renta_seccion_2023 ...")
        conn.exec_driver_sql("TRUNCATE raw.renta_ine_2023;")
        conn.exec_driver_sql("TRUNCATE staging.renta_seccion_2023;")

    logger.info("Insertando %s filas en raw.renta_ine_2023 ...", len(df_raw))
    df_raw.to_sql(
        name="renta_ine_2023",
        con=engine,
        schema="raw",
        if_exists="append",
        index=False,
    )

    logger.info("Insertando %s filas en staging.renta_seccion_2023 ...", len(df_staging))
    df_staging.to_sql(
        name="renta_seccion_2023",
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
            MAX(CASE WHEN indicador = 'renta_media_persona' THEN valor END) AS renta_media_persona,
            MAX(CASE WHEN indicador = 'renta_media_hogar' THEN valor END) AS renta_media_hogar,
            :fuente AS fuente,
            NOW() AS updated_at
        FROM staging.renta_seccion_2023
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
        conn.execute(upsert_sql, {"fuente": FUENTE})

        logger.info("Actualizando marts.v_income_level ...")
        run_sql_file(conn, PROJECT_ROOT / "sql" / "marts" / "011_v_income_level.sql")

        if refresh_features_panel:
            logger.info("Recreando marts.mijas_features_panel ...")
            for sql_file in FEATURE_PANEL_FILES:
                run_sql_file(conn, sql_file)

        summary = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS n_secciones,
                    MIN(renta_media_persona) AS min_persona,
                    MAX(renta_media_persona) AS max_persona,
                    MIN(renta_media_hogar) AS min_hogar,
                    MAX(renta_media_hogar) AS max_hogar
                FROM core.renta_seccion
                WHERE anio = 2023;
                """
            )
        ).mappings().one()

    logger.info(
        "Resumen renta 2023: %s secciones, persona %s-%s, hogar %s-%s",
        summary["n_secciones"],
        summary["min_persona"],
        summary["max_persona"],
        summary["min_hogar"],
        summary["max_hogar"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Ruta al CSV del INE de renta por sección censal",
    )
    parser.add_argument(
        "--refresh-features-panel",
        action="store_true",
        help="Recrear marts.mijas_features_panel para exponer columnas de renta",
    )
    args = parser.parse_args()

    load_renta_ine(args.csv_path, refresh_features_panel=args.refresh_features_panel)
