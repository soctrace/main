import re
import pandas as pd

from etl.common.db import get_engine
from etl.common.logging_utils import get_logger


logger = get_logger(__name__)


def normalize_genero(value: str) -> str | None:
    if value is None:
        return None

    v = str(value).strip().lower()

    if v in ["h", "hombre", "hombres", "varon", "varones"]:
        return "H"
    if v in ["m", "mujer", "mujeres"]:
        return "M"

    return None


def normalize_edad_cohorte(value: str) -> str | None:
    if value is None:
        return None

    v = str(value).strip().lower()

    replacements = {
        "de 0 a 4 años": "0-4",
        "de 5 a 9 años": "5-9",
        "de 10 a 14 años": "10-14",
        "de 15 a 19 años": "15-19",
        "de 20 a 24 años": "20-24",
        "de 25 a 29 años": "25-29",
        "de 30 a 34 años": "30-34",
        "de 35 a 39 años": "35-39",
        "de 40 a 44 años": "40-44",
        "de 45 a 49 años": "45-49",
        "de 50 a 54 años": "50-54",
        "de 55 a 59 años": "55-59",
        "de 60 a 64 años": "60-64",
        "de 65 a 69 años": "65-69",
        "de 70 a 74 años": "70-74",
        "de 75 a 79 años": "75-79",
        "de 80 a 84 años": "80-84",
        "de 85 a 89 años": "85-89",
        "de 90 a 94 años": "90-94",
        "de 95 a 99 años": "95-99",
        "100 y más años": "100+",
    }

    return replacements.get(v, value)


def transform_fact_genero_edad() -> None:
    engine = get_engine()

    logger.info("Leyendo raw.demografia_genero_edad_2023 ...")
    df = pd.read_sql("SELECT * FROM raw.demografia_genero_edad_2023", engine)

    logger.info("Filas raw: %s", len(df))

    df["sexo"] = df["sexo"].apply(normalize_genero)
    df["genero"] = df["genero"].apply(normalize_genero)
    df["edad_cohorte"] = df["edad_cohorte"].apply(normalize_edad_cohorte)
    df["anio"] = pd.to_numeric(df["periodo"], errors="coerce").astype("Int64")
    df["poblacion"] = pd.to_numeric(df["poblacion"], errors="coerce").astype("Int64")

    df = df[
        [
            "seccion_id",
            "sexo",
            "genero",
            "edad_cohorte",
            "anio",
            "poblacion",
            "source_file",
        ]
    ].copy()

    logger.info("Filas staging: %s", len(df))
    logger.info("Valores únicos sexo: %s", df["sexo"].dropna().unique().tolist())
    logger.info("Valores únicos genero: %s", df["genero"].dropna().unique().tolist())

    logger.info("Vaciando staging.fact_genero_edad ...")
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE staging.fact_genero_edad;")

    logger.info("Insertando en staging.fact_genero_edad ...")
    df.to_sql(
        name="fact_genero_edad",
        con=engine,
        schema="staging",
        if_exists="append",
        index=False
    )

    logger.info("Transformación completada.")


if __name__ == "__main__":
    transform_fact_genero_edad()