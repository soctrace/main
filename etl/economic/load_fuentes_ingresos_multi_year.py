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
    PROJECT_ROOT / "data" / "raw" / "ine" / "29070_Mijas_FuenteIngresos_2019_2023.csv"
)
FUENTE = "INE - Atlas de Distribución de Renta"
YEARS = (2019, 2020, 2021, 2022, 2023)
UNIDAD = "porcentaje"

DDL_FILES = [
    PROJECT_ROOT / "sql" / "raw" / "006_create_raw_fuentes_ingresos_2019_2023.sql",
    PROJECT_ROOT / "sql" / "staging" / "007_create_staging_fuentes_ingresos_seccion.sql",
    PROJECT_ROOT / "sql" / "core" / "006_create_core_fuentes_ingresos_seccion.sql",
    PROJECT_ROOT / "sql" / "marts" / "017_v_income_sources.sql",
]


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_column_name(value: str) -> str:
    value = strip_accents(value).strip().lower()
    value = value.replace(" ", "_").replace("__", "_")

    if value == "distribucion_por_fuente_de_ingresos":
        return "distribucion_fuente_ingresos"

    return value


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return strip_accents(str(value)).strip().lower()


def extract_seccion_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None

    match = re.search(r"\b(\d{10})\b", str(value))
    return match.group(1) if match else None


def normalize_indicador(value: object) -> str | None:
    normalized = normalize_text(value)

    if "salario" in normalized:
        return "income_salary"
    if "pensiones" in normalized or "pension" in normalized:
        return "income_pension"
    if "desempleo" in normalized:
        return "income_unemployment"
    if "otras prestaciones" in normalized or "prestaciones sociales" in normalized:
        return "income_social_benefits"
    if "otros ingresos" in normalized or "otras fuentes" in normalized:
        return "income_other"

    return None


def parse_ine_number(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None

    raw = str(value).strip()
    if raw in {"", ".."}:
        return None

    raw = raw.replace("%", "").replace("€", "").strip()
    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    else:
        # INE Spanish thousands separator. These source values are percentages,
        # but this keeps the parser robust for future files with thousands.
        normalized = raw.replace(".", "")

    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"No se pudo convertir Total='{value}' a número INE") from exc


def run_sql_file(conn, path: Path) -> None:
    logger.info("Ejecutando SQL: %s", path.relative_to(PROJECT_ROOT))
    conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def prepare_raw(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    raw = df.copy()
    raw.columns = [normalize_column_name(c) for c in raw.columns]
    expected = [
        "municipios",
        "distritos",
        "secciones",
        "distribucion_fuente_ingresos",
        "periodo",
        "total",
    ]
    missing = [column for column in expected if column not in raw.columns]
    if missing:
        raise ValueError(f"Faltan columnas esperadas: {missing}")

    raw = raw[expected].copy()
    raw["source_file"] = source_file
    return raw


def prepare_staging(raw: pd.DataFrame, source_file: str) -> pd.DataFrame:
    staging = pd.DataFrame(
        {
            "seccion_id": raw["secciones"].apply(extract_seccion_id),
            "anio": pd.to_numeric(raw["periodo"], errors="coerce").astype("Int64"),
            "indicador_original": raw["distribucion_fuente_ingresos"],
            "indicador_norm": raw["distribucion_fuente_ingresos"].apply(normalize_indicador),
            "valor": raw["total"].apply(parse_ine_number),
            "unidad": UNIDAD,
            "source_file": source_file,
        }
    )
    staging = staging[staging["anio"].isin(YEARS)].copy()
    staging = staging.dropna(subset=["seccion_id", "anio", "indicador_original", "indicador_norm", "valor"])
    staging["anio"] = staging["anio"].astype(int)

    invalid_section_ids = staging.loc[~staging["seccion_id"].str.match(r"^\d{10}$"), "seccion_id"].unique()
    if len(invalid_section_ids) > 0:
        raise ValueError(f"seccion_id no válidos: {invalid_section_ids.tolist()}")

    duplicates = staging.duplicated(subset=["seccion_id", "anio", "indicador_norm"], keep=False)
    if duplicates.any():
        duplicated_rows = staging.loc[duplicates, ["seccion_id", "anio", "indicador_norm"]]
        raise ValueError(f"Duplicados en staging: {duplicated_rows.drop_duplicates().to_dict('records')}")

    return staging


def load_fuentes_ingresos_multi_year(csv_path: str | Path = DEFAULT_CSV_PATH) -> None:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    source_file = path.name
    logger.info("Leyendo CSV INE fuentes de ingresos: %s", path)
    raw = prepare_raw(read_csv_safe(path, dtype=str), source_file)
    staging = prepare_staging(raw, source_file)

    raw_indicators = sorted(raw["distribucion_fuente_ingresos"].dropna().unique().tolist())
    normalized_indicators = sorted(staging["indicador_norm"].dropna().unique().tolist())
    logger.info("Indicadores originales detectados: %s", raw_indicators)
    logger.info("Indicadores normalizados detectados: %s", normalized_indicators)
    logger.info("Filas raw: %s; filas staging válidas: %s", len(raw), len(staging))

    engine = get_engine()
    with engine.begin() as conn:
        for ddl_file in DDL_FILES:
            run_sql_file(conn, ddl_file)

        logger.info("Limpiando raw/staging para source_file=%s ...", source_file)
        conn.execute(
            text("DELETE FROM raw.fuentes_ingresos_2019_2023 WHERE source_file = :source_file"),
            {"source_file": source_file},
        )
        conn.execute(
            text(
                """
                DELETE FROM staging.fuentes_ingresos_seccion
                WHERE source_file = :source_file
                   OR anio = ANY(:years)
                """
            ),
            {"source_file": source_file, "years": list(YEARS)},
        )

    logger.info("Insertando %s filas en raw.fuentes_ingresos_2019_2023 ...", len(raw))
    raw.to_sql(
        name="fuentes_ingresos_2019_2023",
        con=engine,
        schema="raw",
        if_exists="append",
        index=False,
    )

    logger.info("Insertando %s filas en staging.fuentes_ingresos_seccion ...", len(staging))
    staging.to_sql(
        name="fuentes_ingresos_seccion",
        con=engine,
        schema="staging",
        if_exists="append",
        index=False,
    )

    upsert_sql = text(
        """
        INSERT INTO core.fuentes_ingresos_seccion (
            seccion_id,
            anio,
            indicador_norm,
            indicador_original,
            valor,
            unidad,
            fuente,
            updated_at
        )
        SELECT
            seccion_id,
            anio,
            indicador_norm,
            MAX(indicador_original) AS indicador_original,
            MAX(valor) AS valor,
            MAX(unidad) AS unidad,
            :fuente AS fuente,
            NOW() AS updated_at
        FROM staging.fuentes_ingresos_seccion
        WHERE anio = ANY(:years)
        GROUP BY seccion_id, anio, indicador_norm
        ON CONFLICT (seccion_id, anio, indicador_norm)
        DO UPDATE SET
            valor = EXCLUDED.valor,
            indicador_original = EXCLUDED.indicador_original,
            unidad = EXCLUDED.unidad,
            fuente = EXCLUDED.fuente,
            updated_at = NOW();
        """
    )

    with engine.begin() as conn:
        logger.info("Upsert en core.fuentes_ingresos_seccion ...")
        result = conn.execute(upsert_sql, {"fuente": FUENTE, "years": list(YEARS)})
        logger.info("Filas insertadas/actualizadas en core: %s", result.rowcount)
        run_sql_file(conn, PROJECT_ROOT / "sql" / "marts" / "017_v_income_sources.sql")

        summary = conn.execute(
            text(
                """
                SELECT
                    anio,
                    COUNT(*) AS filas,
                    COUNT(DISTINCT seccion_id) AS secciones,
                    COUNT(DISTINCT indicador_norm) AS indicadores
                FROM core.fuentes_ingresos_seccion
                GROUP BY anio
                ORDER BY anio;
                """
            )
        ).mappings().all()

    for row in summary:
        logger.info(
            "Fuentes ingresos %s: %s filas, %s secciones, %s indicadores",
            row["anio"],
            row["filas"],
            row["secciones"],
            row["indicadores"],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Ruta al CSV multi-año de fuentes de ingresos por sección censal",
    )
    args = parser.parse_args()

    load_fuentes_ingresos_multi_year(args.csv_path)
