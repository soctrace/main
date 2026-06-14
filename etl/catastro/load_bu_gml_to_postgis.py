from pathlib import Path
import geopandas as gpd
from sqlalchemy import create_engine, text

GML_DIR = Path("data/raw/catastro/cartografia/bu")
DB_URL = "postgresql:///mijas"

engine = create_engine(DB_URL)

# ⚠️ Ajustamos patrón flexible
files = list(GML_DIR.glob("*buildingpart.gml"))

print(f"Encontrados {len(files)} ficheros GML")

if not files:
    raise FileNotFoundError(f"No hay GML en {GML_DIR.resolve()}")

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
    conn.execute(text("DROP TABLE IF EXISTS staging.catastro_bu_raw"))

first = True

for file in files:
    print(f"Leyendo: {file.name}")

    try:
        gdf = gpd.read_file(file)
    except Exception as e:
        print(f"❌ Error leyendo {file.name}: {e}")
        continue

    if gdf.empty:
        print(f"Vacío: {file.name}")
        continue

    gdf = gdf.to_crs(epsg=4326)
    gdf["source_file"] = file.name

    gdf.to_postgis(
        "catastro_bu_raw",
        engine,
        schema="staging",
        if_exists="replace" if first else "append",
        index=False
    )

    first = False

print("✅ Carga completada en staging.catastro_bu_raw")