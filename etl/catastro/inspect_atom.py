from pathlib import Path
import xml.etree.ElementTree as ET

ATOM_FILE = Path("data/raw/catastro/cartografia/ES.SDGC.CP.atom.xml")

tree = ET.parse(ATOM_FILE)
root = tree.getroot()

print("ROOT:", root.tag)

print("\n=== TODOS LOS LINKS ENCONTRADOS ===")

count = 0

for elem in root.iter():
    if elem.tag.endswith("link"):
        count += 1
        href = elem.attrib.get("href")
        rel = elem.attrib.get("rel")
        type_ = elem.attrib.get("type")
        title = elem.attrib.get("title")

        print("-" * 80)
        print("href :", href)
        print("rel  :", rel)
        print("type :", type_)
        print("title:", title)

print(f"\nTotal links encontrados: {count}")