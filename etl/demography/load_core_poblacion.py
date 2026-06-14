import pandas as pd

from etl.common.db import get_engine
from etl.common.logging_utils import get_logger

logger = get_logger(__name__)


def load_core_poblacion_edad():
    engine = get_engine()

    logger.info("Leyendo staging.fact_genero_edad ...")
    df = pd.read_sql("SELECT * FROM staging.fact_genero_edad", engine)

    logger.info("Filas staging: %s", len(df))

    # Nos quedamos con columnas core
    df = df[
        [
            "seccion_id",
            "anio",
            "genero",
            "edad_cohorte",
            "poblacion",
        ]
    ].copy()

    # Validación básica
    df = df.dropna()

    logger.info("Filas tras limpieza: %s", len(df))

    # Evitar duplicados
    df = df.drop_duplicates(
        subset=["seccion_id", "anio", "genero", "edad_cohorte"]
    )

    logger.info("Filas tras deduplicación: %s", len(df))

    logger.info("Vaciando core.poblacion_edad ...")
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE core.poblacion_edad;")

    logger.info("Insertando en core.poblacion_edad ...")
    df.to_sql(
        name="poblacion_edad",
        con=engine,
        schema="core",
        if_exists="append",
        index=False
    )

    logger.info("Carga en core completada.")


if __name__ == "__main__":
    load_core_poblacion_edad()