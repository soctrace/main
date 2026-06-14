from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from etl.common.db import get_engine
from etl.common.io import read_csv_safe
from etl.common.logging_utils import get_logger


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "ine"
FUENTE = "INE - Atlas de Distribución de Renta"

DDL_FILES = [
    PROJECT_ROOT / "sql" / "raw" / "007_create_raw_ine_socioeconomic.sql",
    PROJECT_ROOT / "sql" / "staging" / "008_create_staging_socioeconomic_indicator_section.sql",
    PROJECT_ROOT / "sql" / "core" / "008_create_core_socioeconomic_indicators.sql",
    PROJECT_ROOT / "sql" / "marts" / "020_socioeconomic_intelligence.sql",
]


@dataclass(frozen=True)
class SourceConfig:
    path: Path
    raw_table: str
    domain: str
    indicator_code: str
    category_column: str
    years: tuple[int, ...]
    value_type: str
    unit: str
    indicator_label: str
    requires_total_sex: bool = False


SOURCES = [
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_NivelEstudios_2021_2024.csv",
        raw_table="ine_nivel_estudios_2021_2024",
        domain="education_level",
        indicator_code="education_level",
        category_column="nivel_formacion_alcanzado",
        years=(2021, 2022, 2023, 2024),
        value_type="count",
        unit="persons",
        indicator_label="Nivel de formación alcanzado",
        requires_total_sex=True,
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_Ocupacion_2021_2024.csv",
        raw_table="ine_ocupacion_2021_2024",
        domain="occupation_status",
        indicator_code="occupation_status",
        category_column="relacion_actividad",
        years=(2021, 2022, 2023, 2024),
        value_type="count",
        unit="persons",
        indicator_label="Relación con la actividad",
        requires_total_sex=True,
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_Actividad_2021_2023.csv",
        raw_table="ine_actividad_2021_2023",
        domain="occupation_activity",
        indicator_code="occupation_activity",
        category_column="ocupacion",
        years=(2021, 2022, 2023),
        value_type="count",
        unit="persons",
        indicator_label="Ocupación",
        requires_total_sex=True,
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_RamaActividad_2021_2023.csv",
        raw_table="ine_rama_actividad_2021_2023",
        domain="activity_branch",
        indicator_code="activity_branch",
        category_column="actividad_economica",
        years=(2021, 2022, 2023),
        value_type="count",
        unit="persons",
        indicator_label="Actividad económica",
        requires_total_sex=True,
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_SitProfesional_2021_2023.csv",
        raw_table="ine_sit_profesional_2021_2023",
        domain="professional_status",
        indicator_code="professional_status",
        category_column="situacion_profesional",
        years=(2021, 2022, 2023),
        value_type="count",
        unit="persons",
        indicator_label="Situación profesional",
        requires_total_sex=True,
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_IndiceGini_DistribucionRenta_2015_2023.csv",
        raw_table="ine_gini_p80p20_2015_2023",
        domain="income_inequality",
        indicator_code="income_inequality",
        category_column="indicador",
        years=(2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023),
        value_type="index",
        unit="index",
        indicator_label="Índice Gini y distribución P80/P20",
    ),
    SourceConfig(
        path=RAW_DIR / "29070_Mijas_FuenteIngresos_2019_2023.csv",
        raw_table="ine_fuente_ingresos_2019_2023",
        domain="income_source",
        indicator_code="income_source",
        category_column="distribucion_fuente_ingresos",
        years=(2019, 2020, 2021, 2022, 2023),
        value_type="percentage",
        unit="percent",
        indicator_label="Distribución por fuente de ingresos",
    ),
]


CATEGORY_MAP: dict[str, dict[str, tuple[str, str, int]]] = {
    "education_level": {
        "total": ("total", "Total", 0),
        "educacion primaria e inferior": ("primary_or_below", "Educación primaria e inferior", 10),
        "primera etapa de educacion secundaria y similar": (
            "lower_secondary",
            "Primera etapa de Educación Secundaria y similar",
            20,
        ),
        "segunda etapa de educacion secundaria y educacion postsecundaria no superior": (
            "upper_secondary",
            "Segunda etapa de Educación Secundaria y Educación Postsecundaria no Superior",
            30,
        ),
        "educacion superior": ("higher", "Educación superior", 40),
    },
    "occupation_status": {
        "total": ("total", "Total", 0),
        "ocupado/a": ("employed", "Ocupado/a", 10),
        "parado/a": ("unemployed", "Parado/a", 20),
        "estudiante": ("student", "Estudiante", 30),
        "perceptor/a pension de incapacidad, jubilacion, prejubilacion": (
            "pensioner",
            "Perceptor/a pensión de incapacidad, jubilación, prejubilación",
            40,
        ),
        "otra situacion de inactividad": (
            "other_inactive",
            "Otra situación de inactividad",
            50,
        ),
    },
    "occupation_activity": {
        "total": ("total", "Total", 0),
        "directores/gerentes y profesionales/tecnicos de nivel medio o alto": (
            "directors_managers_professionals",
            "Directores/gerentes y profesionales/técnicos de nivel medio o alto",
            10,
        ),
        "trabajadores cualificados y oficiales/operarios de nivel bajo": (
            "skilled_workers",
            "Trabajadores cualificados y oficiales/operarios de nivel bajo",
            20,
        ),
        "ocupaciones elementales": ("elementary_occupations", "Ocupaciones elementales", 30),
        "no consta": ("unknown", "No consta", 90),
    },
    "activity_branch": {
        "total cnae": ("total", "Total CNAE", 0),
        "agricultura, ganaderia y pesca": (
            "agriculture",
            "Agricultura, ganadería y pesca",
            10,
        ),
        "industria": ("industry", "Industria", 20),
        "construccion": ("construction", "Construcción", 30),
        "servicios": ("services", "Servicios", 40),
        "no consta": ("unknown", "No consta", 90),
    },
    "professional_status": {
        "total": ("total", "Total", 0),
        "trabajador por cuenta propia": (
            "self_employed",
            "Trabajador por cuenta propia",
            10,
        ),
        "trabajador por cuenta ajena y otra situacion": (
            "employee_or_other",
            "Trabajador por cuenta ajena y otra situación",
            20,
        ),
    },
    "income_inequality": {
        "indice de gini": ("gini_index", "Índice de Gini", 10),
        "distribucion de la renta p80/p20": (
            "p80_p20_ratio",
            "Distribución de la renta P80/P20",
            20,
        ),
    },
    "income_source": {
        "fuente de ingreso: salario": ("salary", "Fuente de ingreso: salario", 10),
        "fuente de ingreso: pensiones": ("pension", "Fuente de ingreso: pensiones", 20),
        "fuente de ingreso: prestaciones por desempleo": (
            "unemployment_benefits",
            "Fuente de ingreso: prestaciones por desempleo",
            30,
        ),
        "fuente de ingreso: otras prestaciones": (
            "social_benefits",
            "Fuente de ingreso: otras prestaciones",
            40,
        ),
        "fuente de ingreso: otros ingresos": (
            "other_income",
            "Fuente de ingreso: otros ingresos",
            50,
        ),
    },
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_column_name(value: str) -> str:
    normalized = strip_accents(value).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    replacements = {
        "nivel_de_formacion_alcanzado": "nivel_formacion_alcanzado",
        "relacion_con_la_actividad": "relacion_actividad",
        "actividad_economica": "actividad_economica",
        "situacion_profesional": "situacion_profesional",
        "indice_de_gini_y_distribucion_de_la_renta_p80_p20": "indicador",
        "distribucion_por_fuente_de_ingresos": "distribucion_fuente_ingresos",
    }
    return replacements.get(normalized, normalized)


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    value = strip_accents(str(value)).strip().lower()
    return re.sub(r"\s+", " ", value)


def extract_seccion_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"\b(\d{10})\b", str(value))
    return match.group(1) if match else None


def parse_spanish_number(value: object, value_type: str) -> Decimal | None:
    if value is None or pd.isna(value):
        return None

    raw = str(value).strip()
    if raw in {"", "..", "."}:
        return None

    raw = raw.replace("%", "").replace("€", "").strip()
    if "," in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif value_type == "count":
        normalized = raw.replace(".", "")
    else:
        normalized = raw

    try:
        return Decimal(normalized).quantize(Decimal("0.0001"))
    except InvalidOperation as exc:
        raise ValueError(f"No se pudo convertir Total='{value}' a número INE") from exc


def map_category(config: SourceConfig, original: object) -> tuple[str, str, int]:
    normalized = normalize_text(original)
    mapped = CATEGORY_MAP.get(config.domain, {}).get(normalized)
    if mapped:
        return mapped
    return ("other", str(original).strip() if original is not None else "Other", 999)


def raw_columns_for(config: SourceConfig) -> list[str]:
    columns = ["provincias", "municipios", "secciones"]
    if config.raw_table.startswith("ine_gini") or config.raw_table.startswith("ine_fuente"):
        columns = ["municipios", "distritos", "secciones"]
    if config.requires_total_sex:
        columns.append("sexo")
    columns.extend([config.category_column, "periodo", "total"])
    return columns


def read_source(config: SourceConfig) -> pd.DataFrame:
    if not config.path.exists():
        raise FileNotFoundError(f"No existe el fichero: {config.path}")

    df = read_csv_safe(config.path, dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    expected = raw_columns_for(config)
    missing = [column for column in expected if column not in df.columns]
    if missing:
        raise ValueError(f"{config.path.name}: faltan columnas esperadas {missing}")

    raw = df[expected].copy()
    raw["source_file"] = config.path.name
    return raw


def prepare_staging(config: SourceConfig, raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    if config.requires_total_sex:
        frame = frame[frame["sexo"].apply(normalize_text).eq("total")].copy()

    mapped_categories = frame[config.category_column].apply(lambda value: map_category(config, value))
    value_types = []
    units = []
    for category_code, _, _ in mapped_categories:
        if config.domain == "income_inequality" and category_code == "p80_p20_ratio":
            value_types.append("ratio")
            units.append("ratio")
        else:
            value_types.append(config.value_type)
            units.append(config.unit)

    staging = pd.DataFrame(
        {
            "seccion_id": frame["secciones"].apply(extract_seccion_id),
            "anio": pd.to_numeric(frame["periodo"], errors="coerce").astype("Int64"),
            "domain": config.domain,
            "indicator_code": config.indicator_code,
            "category_code": [category[0] for category in mapped_categories],
            "indicator_label": config.indicator_label,
            "category_label": [category[1] for category in mapped_categories],
            "value": [
                parse_spanish_number(value, value_type)
                for value, value_type in zip(frame["total"], value_types, strict=True)
            ],
            "value_type": value_types,
            "unit": units,
            "source_file": config.path.name,
        }
    )

    staging = staging[staging["anio"].isin(config.years)].copy()
    staging = staging.dropna(subset=["seccion_id", "anio", "category_code", "value"])
    staging["anio"] = staging["anio"].astype(int)

    invalid_ids = staging.loc[~staging["seccion_id"].str.match(r"^\d{10}$"), "seccion_id"].unique()
    if len(invalid_ids) > 0:
        raise ValueError(f"{config.path.name}: seccion_id no válidos {invalid_ids.tolist()}")

    duplicates = staging.duplicated(
        subset=["seccion_id", "anio", "domain", "indicator_code", "category_code"],
        keep=False,
    )
    if duplicates.any():
        duplicated_rows = staging.loc[
            duplicates,
            ["seccion_id", "anio", "domain", "indicator_code", "category_code"],
        ]
        raise ValueError(
            f"{config.path.name}: duplicados en staging "
            f"{duplicated_rows.drop_duplicates().to_dict('records')}"
        )

    return staging


def build_catalog(staging: pd.DataFrame) -> pd.DataFrame:
    catalog = staging[
        [
            "domain",
            "indicator_code",
            "category_code",
            "indicator_label",
            "category_label",
            "value_type",
            "unit",
        ]
    ].drop_duplicates()

    sort_lookup: dict[tuple[str, str], int] = {}
    for domain, categories in CATEGORY_MAP.items():
        for _, (category_code, _, sort_order) in categories.items():
            sort_lookup[(domain, category_code)] = sort_order

    catalog["sort_order"] = catalog.apply(
        lambda row: sort_lookup.get((row["domain"], row["category_code"]), 999),
        axis=1,
    )
    catalog["is_synthetic"] = False
    catalog["description"] = None
    return catalog.sort_values(["domain", "indicator_code", "sort_order", "category_code"])


def run_sql_file(conn, path: Path) -> None:
    logger.info("Ejecutando SQL: %s", path.relative_to(PROJECT_ROOT))
    conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def load_socioeconomic_indicators() -> None:
    raw_by_source: dict[SourceConfig, pd.DataFrame] = {}
    staging_frames: list[pd.DataFrame] = []

    for config in SOURCES:
        logger.info("Leyendo fuente socioeconómica: %s", config.path)
        raw = read_source(config)
        staging = prepare_staging(config, raw)
        raw_by_source[config] = raw
        staging_frames.append(staging)

        unknown_categories = sorted(
            staging.loc[staging["category_code"].eq("other"), "category_label"].unique().tolist()
        )
        logger.info(
            "%s: raw=%s, staging=%s, años=%s, secciones=%s, categorías=%s, other=%s",
            config.domain,
            len(raw),
            len(staging),
            sorted(staging["anio"].unique().tolist()),
            staging["seccion_id"].nunique(),
            sorted(staging["category_code"].unique().tolist()),
            unknown_categories,
        )

    staging_all = pd.concat(staging_frames, ignore_index=True)
    catalog = build_catalog(staging_all)
    domains = sorted(staging_all["domain"].unique().tolist())

    engine = get_engine()
    with engine.begin() as conn:
        for ddl_file in DDL_FILES[:-1]:
            run_sql_file(conn, ddl_file)

        for config, raw in raw_by_source.items():
            logger.info("Limpiando raw.%s para %s", config.raw_table, config.path.name)
            conn.execute(
                text(f"DELETE FROM raw.{config.raw_table} WHERE source_file = :source_file"),
                {"source_file": config.path.name},
            )

        logger.info("Limpiando staging/core socioeconómico para dominios: %s", domains)
        conn.execute(
            text(
                """
                DELETE FROM staging.socioeconomic_indicator_section
                WHERE domain = ANY(:domains)
                """
            ),
            {"domains": domains},
        )
        conn.execute(
            text(
                """
                DELETE FROM core.socioeconomic_indicator_section
                WHERE domain = ANY(:domains)
                  AND fuente = :fuente
                """
            ),
            {"domains": domains, "fuente": FUENTE},
        )

    for config, raw in raw_by_source.items():
        logger.info("Insertando %s filas en raw.%s", len(raw), config.raw_table)
        raw.to_sql(
            name=config.raw_table,
            con=engine,
            schema="raw",
            if_exists="append",
            index=False,
        )

    logger.info("Insertando %s filas en staging.socioeconomic_indicator_section", len(staging_all))
    staging_all.to_sql(
        name="socioeconomic_indicator_section",
        con=engine,
        schema="staging",
        if_exists="append",
        index=False,
    )

    with engine.begin() as conn:
        logger.info("Upsert catálogo socioeconómico: %s filas", len(catalog))
        conn.execute(
            text(
                """
                INSERT INTO core.socioeconomic_indicator_catalog (
                    domain,
                    indicator_code,
                    category_code,
                    indicator_label,
                    category_label,
                    value_type,
                    unit,
                    sort_order,
                    is_synthetic,
                    description
                )
                VALUES (
                    :domain,
                    :indicator_code,
                    :category_code,
                    :indicator_label,
                    :category_label,
                    :value_type,
                    :unit,
                    :sort_order,
                    :is_synthetic,
                    :description
                )
                ON CONFLICT (domain, indicator_code, category_code)
                DO UPDATE SET
                    indicator_label = EXCLUDED.indicator_label,
                    category_label = EXCLUDED.category_label,
                    value_type = EXCLUDED.value_type,
                    unit = EXCLUDED.unit,
                    sort_order = EXCLUDED.sort_order,
                    is_synthetic = EXCLUDED.is_synthetic,
                    description = EXCLUDED.description
                """
            ),
            catalog.to_dict("records"),
        )

        logger.info("Upsert core.socioeconomic_indicator_section")
        result = conn.execute(
            text(
                """
                INSERT INTO core.socioeconomic_indicator_section (
                    seccion_id,
                    anio,
                    domain,
                    indicator_code,
                    category_code,
                    indicator_label,
                    category_label,
                    value,
                    value_type,
                    unit,
                    source_file,
                    fuente,
                    updated_at
                )
                SELECT
                    seccion_id,
                    anio,
                    domain,
                    indicator_code,
                    category_code,
                    MAX(indicator_label) AS indicator_label,
                    MAX(category_label) AS category_label,
                    MAX(value) AS value,
                    MAX(value_type) AS value_type,
                    MAX(unit) AS unit,
                    MAX(source_file) AS source_file,
                    :fuente AS fuente,
                    NOW() AS updated_at
                FROM staging.socioeconomic_indicator_section
                WHERE domain = ANY(:domains)
                GROUP BY
                    seccion_id,
                    anio,
                    domain,
                    indicator_code,
                    category_code
                ON CONFLICT (
                    seccion_id,
                    anio,
                    domain,
                    indicator_code,
                    category_code
                )
                DO UPDATE SET
                    value = EXCLUDED.value,
                    indicator_label = EXCLUDED.indicator_label,
                    category_label = EXCLUDED.category_label,
                    value_type = EXCLUDED.value_type,
                    unit = EXCLUDED.unit,
                    source_file = EXCLUDED.source_file,
                    fuente = EXCLUDED.fuente,
                    updated_at = NOW()
                """
            ),
            {"domains": domains, "fuente": FUENTE},
        )
        logger.info("Filas insertadas/actualizadas en core: %s", result.rowcount)

        run_sql_file(conn, DDL_FILES[-1])

        summary = conn.execute(
            text(
                """
                SELECT
                    domain,
                    anio,
                    COUNT(*) AS rows,
                    COUNT(DISTINCT seccion_id) AS secciones,
                    COUNT(DISTINCT category_code) AS categorias
                FROM core.socioeconomic_indicator_section
                GROUP BY domain, anio
                ORDER BY domain, anio
                """
            )
        ).mappings().all()

        other_rows = conn.execute(
            text(
                """
                SELECT DISTINCT domain, category_label
                FROM core.socioeconomic_indicator_section
                WHERE category_code = 'other'
                ORDER BY domain, category_label
                """
            )
        ).mappings().all()

    for row in summary:
        logger.info(
            "%s %s: %s filas, %s secciones, %s categorías",
            row["domain"],
            row["anio"],
            row["rows"],
            row["secciones"],
            row["categorias"],
        )

    if other_rows:
        logger.warning("Categorías other pendientes: %s", [dict(row) for row in other_rows])
    else:
        logger.info("No hay categorías socioeconómicas mapeadas como other.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    load_socioeconomic_indicators()
