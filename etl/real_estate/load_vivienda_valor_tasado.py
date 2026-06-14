from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

BASE_PATH = Path("data/raw/vivienda/ministerio")
DB_URL = "postgresql:///mijas"

engine = create_engine(DB_URL)

# Ajusta el nombre cuando tengas el fichero descargado
FILE = BASE_PATH / "valor_tasado_municipios_25000.xls"

print(f"Leyendo: {FILE}")

if FILE.suffix.lower() in [".xlsx", ".xls"]:
    xls = pd.ExcelFile(FILE)
    print("Hojas disponibles:", xls.sheet_names)

    # Ajustar sheet_name si hiciera falta
    df = pd.read_excel(FILE, sheet_name=0)
else:
    df = pd.read_csv(FILE, sep=None, engine="python", encoding="latin1")

df.columns = [
    str(c).strip().lower()
    .replace(" ", "_")
    .replace(".", "")
    .replace("á", "a")
    .replace("é", "e")
    .replace("í", "i")
    .replace("ó", "o")
    .replace("ú", "u")
    .replace("ñ", "n")
    for c in df.columns
]

print(df.head())
print(df.columns.tolist())

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))

df.to_sql(
    "vivienda_valor_tasado_municipio_raw",
    engine,
    schema="staging",
    if_exists="replace",
    index=False,
)

print("✅ Cargado staging.vivienda_valor_tasado_municipio_raw")