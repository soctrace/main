from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.common.db import get_engine

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "raw" / "vivienda" / "manual"
DEFAULT_FILENAMES = (
    "[Mijas] Metro Cuadrado precio.xlsx",
    "[Mijas] Metro Cuadrado precio.xls",
    "[Mijas] Metro Cuadrado precio.csv",
)
EXPECTED_SECTIONS = 37

SECTION_CANDIDATES = (
    "seccion_id",
    "section_id",
    "cusec",
    "cod_seccion",
    "codigo_seccion",
    "seccion",
)
PRICE_CANDIDATES = (
    "precio_m2_observado",
    "precio_m2",
    "eur_m2",
    "euros_m2",
    "€/m2",
    "€/m²",
    "metro_cuadrado",
    "precio",
)


def normalize_column_name(value: object) -> str:
    text_value = unicodedata.normalize("NFKD", str(value).strip().lower())
    text_value = "".join(char for char in text_value if not unicodedata.combining(char))
    text_value = text_value.replace("€/m²", "eur_m2").replace("€/m2", "eur_m2")
    text_value = re.sub(r"[^a-z0-9]+", "_", text_value)
    return text_value.strip("_")


def parse_euro_number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, int | float):
        return float(value)

    text_value = str(value).strip()
    if not text_value:
        return None

    text_value = re.sub(r"[^\d,.\-]", "", text_value)
    if not text_value:
        return None

    if "," in text_value and "." in text_value:
        text_value = text_value.replace(".", "").replace(",", ".")
    elif "," in text_value:
        text_value = text_value.replace(",", ".")

    try:
        return float(text_value)
    except ValueError:
        return None


def normalize_section_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, int | float):
        if not pd.notna(value):
            return None
        if float(value).is_integer():
            value = str(int(value))

    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None

    if len(digits) == 10:
        return digits

    if len(digits) == 5:
        return f"29070{digits}"

    if len(digits) <= 3:
        return f"2907001{int(digits):03d}"

    if len(digits) == 9 and digits.startswith("2907001"):
        return f"{digits[:7]}0{digits[-2:]}"

    return digits[-10:] if len(digits) > 10 else None


def find_column(columns: list[str], candidates: tuple[str, ...], contains: tuple[str, ...] = ()) -> str:
    for candidate in candidates:
        normalized_candidate = normalize_column_name(candidate)
        if normalized_candidate in columns:
            return normalized_candidate

    for column in columns:
        if all(fragment in column for fragment in contains):
            return column

    raise ValueError(f"No column found for candidates: {', '.join(candidates)}")


def find_input_file(path_arg: str | None) -> Path | None:
    if path_arg:
        path = Path(path_arg).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path

    for filename in DEFAULT_FILENAMES:
        path = DEFAULT_INPUT_DIR / filename
        if path.exists():
            return path

    if DEFAULT_INPUT_DIR.exists():
        candidates = sorted(
            path
            for path in DEFAULT_INPUT_DIR.iterdir()
            if path.suffix.lower() in {".xlsx", ".xls", ".csv"}
        )
        return candidates[0] if candidates else None

    return None


def read_input(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=0)
    if suffix == ".csv":
        return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    raise ValueError(f"Unsupported file extension: {path.suffix}")


def create_empty_table() -> None:
    ddl_path = PROJECT_ROOT / "sql" / "staging" / "003_create_manual_precio_m2_seccion_2023.sql"
    with get_engine().begin() as conn:
        conn.execute(text(ddl_path.read_text()))


def load_prices(path: Path, strict: bool) -> pd.DataFrame:
    raw_df = read_input(path)
    raw_df.columns = [normalize_column_name(column) for column in raw_df.columns]

    section_column = find_column(raw_df.columns.tolist(), SECTION_CANDIDATES, contains=("seccion",))
    price_column = find_column(raw_df.columns.tolist(), PRICE_CANDIDATES, contains=("precio",))

    source_column = "fuente" if "fuente" in raw_df.columns else None
    notes_column = "notas" if "notas" in raw_df.columns else None
    confidence_column = "confidence_level" if "confidence_level" in raw_df.columns else None

    df = pd.DataFrame(
        {
            "seccion_id": raw_df[section_column].map(normalize_section_id),
            "precio_m2_observado": raw_df[price_column].map(parse_euro_number),
            "fuente": raw_df[source_column] if source_column else path.name,
            "notas": raw_df[notes_column] if notes_column else None,
            "confidence_level": raw_df[confidence_column] if confidence_column else "High",
        }
    )

    df["confidence_level"] = (
        df["confidence_level"]
        .fillna("High")
        .astype(str)
        .str.strip()
        .str.title()
        .where(lambda series: series.isin(["High", "Medium", "Low"]), "High")
    )
    df = df.dropna(subset=["seccion_id", "precio_m2_observado"])
    df = df[df["precio_m2_observado"] > 0]
    df = df.drop_duplicates(subset=["seccion_id"], keep="last")
    df = df.sort_values("seccion_id")

    if strict and len(df) != EXPECTED_SECTIONS:
        raise ValueError(
            f"Expected {EXPECTED_SECTIONS} sections, found {len(df)} after cleaning {path.name}"
        )

    create_empty_table()
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE staging.manual_precio_m2_seccion_2023"))
        df.to_sql(
            "manual_precio_m2_seccion_2023",
            conn,
            schema="staging",
            if_exists="append",
            index=False,
            method="multi",
        )

    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load manual section-level observed market references for Mijas 2023."
    )
    parser.add_argument("--file", help="Excel/CSV file path. Defaults to data/raw/vivienda/manual/.")
    parser.add_argument("--strict", action="store_true", help="Fail if the file does not contain 37 sections.")
    args = parser.parse_args()

    path = find_input_file(args.file)
    if path is None or not path.exists():
        create_empty_table()
        print(
            "No manual price file found. Created/kept empty "
            "staging.manual_precio_m2_seccion_2023."
        )
        return

    df = load_prices(path, strict=args.strict)
    missing = EXPECTED_SECTIONS - len(df)
    print(f"Loaded {len(df)} section market references from {path}.")
    if missing:
        print(f"Warning: {missing} of {EXPECTED_SECTIONS} expected sections are missing.")


if __name__ == "__main__":
    main()
