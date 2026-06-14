import os
import requests
import xml.etree.ElementTree as ET

ATOM_FILE = "data/raw/catastro/cartografia/ES.SDGC.CP_29.xml"
OUTPUT_DIR = "data/raw/catastro/cartografia/gml"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_MUNICIPIO = "29070"  # Mijas

NS = {'atom': 'http://www.w3.org/2005/Atom'}

tree = ET.parse(ATOM_FILE)
root = tree.getroot()

links = []

# 🔎 Buscar enlaces a GML o ZIP
for elem in root.iter():
    if elem.tag.endswith("link"):
        href = elem.attrib.get("href")
        if href and (".gml" in href or ".zip" in href):
            links.append(href)

print(f"🔎 Total enlaces encontrados: {len(links)}")

# 🎯 Filtrar Mijas
filtered_links = links
print(f"🎯 Enlaces para Mijas: {len(filtered_links)}")

# ⬇️ Descargar
for url in filtered_links:
    filename = os.path.join(OUTPUT_DIR, url.split("/")[-1])

    if os.path.exists(filename):
        print(f"⏩ Ya existe: {filename}")
        continue

    print(f"⬇️ Descargando: {url}")
    r = requests.get(url, stream=True)

    with open(filename, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

print("✅ Descarga completada")