import os
import requests
import xml.etree.ElementTree as ET

ATOM_FILE = "data/raw/catastro/cartografia/ES.SDGC.BU_29.xml"
OUTPUT_DIR = "data/raw/catastro/cartografia/bu"

os.makedirs(OUTPUT_DIR, exist_ok=True)

tree = ET.parse(ATOM_FILE)
root = tree.getroot()

links = []

for elem in root.iter():
    if elem.tag.endswith("link"):
        href = elem.attrib.get("href")
        if href and (".zip" in href or ".gml" in href):
            links.append(href)

print(f"🔎 Total enlaces encontrados: {len(links)}")

# Para empezar descargamos todos los BU de Málaga.
# Luego filtramos Mijas por PostGIS.
for url in links:
    filename = os.path.join(OUTPUT_DIR, url.split("/")[-1])

    if os.path.exists(filename):
        print(f"⏩ Ya existe: {filename}")
        continue

    print(f"⬇️ Descargando: {url}")
    r = requests.get(url, stream=True)

    with open(filename, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

print("✅ Descarga BU completada")