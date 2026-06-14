import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

BASE_PATH = Path("data/raw/catastro/estadisticas")
DB_URL = "postgresql:///mijas"

files = {
    "valor_medio": "hst_vm_distritos.csv",
    "superficie_media": "hst_supm_distritos.csv",
    "inmuebles": "hst_inm_distritos.csv",
}

engine = create_engine(DB_URL)

dfs = []

for tipo, filename in files.items():
    path = BASE_PATH / filename
    print(f"Leyendo {path}")

    df = pd.read_csv(
        path,
        sep=",",
        encoding="latin1",   # 🔥 clave
        engine="python",
        on_bad_lines="warn"
    )
    df.columns = [c.lower() for c in df.columns]
    df["tipo_estadistica"] = tipo

    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))

df_all.to_sql(
    "catastro_estadistica_distrito",
    engine,
    schema="staging",
    if_exists="replace",
    index=False,
)

print("✅ Cargado staging.catastro_estadistica_distrito")
print(df_all.columns.tolist())
print(df_all.head())