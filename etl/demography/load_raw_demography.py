from pathlib import Path
import argparse

from etl.common.db import get_engine
from etl.common.io import read_csv_safe
from etl.common.logging_utils import get_logger


logger = get_logger(__name__)


def extract_seccion_id(seccion_text: str) -> str:
    """
    Ejemplo entrada:
    '2907001001 Mijas sección 01001'
    Devuelve:
    '2907001001'
    """
    if not isinstance(seccion_text, str):
        return None
    return seccion_text.split()[0]


def load_demography_genero_edad(csv_path: str, table_name: str = "demografia_genero_edad_2023") -> None:
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    logger.info("Leyendo CSV: %s", path)

    df = read_csv_safe(path)

    logger.info("Filas leídas: %s", len(df))
    logger.info("Columnas detectadas: %s", list(df.columns))

    # Renombrar desde nombres del fichero origen a nombres de nuestra tabla raw
    rename_map = {
        "Sexo": "sexo",
        "Edad": "edad_cohorte",
        "Periodo": "periodo",
        "Total": "poblacion",
    }

    df = df.rename(columns=rename_map)

    # Construir seccion_id desde la columna "Secciones"
    if "Secciones" not in df.columns:
        raise ValueError("No existe la columna 'Secciones' en el CSV.")

    df["seccion_id"] = df["Secciones"].apply(extract_seccion_id)

    # Generar columna genero igual a sexo por ahora
    df["genero"] = df["sexo"]

    # Añadir trazabilidad
    df["source_file"] = path.name

    # Nos quedamos solo con las columnas que existen en la tabla raw
    df = df[
        [
            "seccion_id",
            "sexo",
            "genero",
            "edad_cohorte",
            "periodo",
            "poblacion",
            "source_file",
        ]
    ].copy()

    engine = get_engine()

    logger.info("Insertando en raw.%s ...", table_name)
    df.to_sql(
        name=table_name,
        con=engine,
        schema="raw",
        if_exists="append",
        index=False
    )

    logger.info("Carga completada en raw.%s", table_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-path", required=True, help="Ruta al CSV de demografía género-edad")
    args = parser.parse_args()

    load_demography_genero_edad(args.csv_path)