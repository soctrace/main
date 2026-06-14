from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = "postgresql:///mijas"
DEFAULT_SEARCH_DIRS = [
    PROJECT_ROOT / "data/raw/elections/andaluzas",
    Path("/Users/josemanuelguzman/Documents/SOCTRACE/Andaluzas"),
]

LOCAL_PATTERNS = (
    "POR MI PUEBLO",
    "SOYDEMIJAS",
    "SOY DE MIJAS",
    "A.MIJAS",
    "A.MIHA",
    "ALTERNATIVA MIJE",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Mijas 2018 Andalusian section CSVs.")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--resultados", type=Path, default=None)
    parser.add_argument("--datos", type=Path, default=None)
    return parser.parse_args()


def find_source_file(explicit: Path | None, filename: str) -> Path:
    if explicit:
        return explicit

    for directory in DEFAULT_SEARCH_DIRS:
        candidate = directory / filename
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Could not find {filename} in known Andaluzas source folders")


def parse_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    text_value = str(value).strip().replace(".", "")
    if "," in text_value:
        text_value = text_value.split(",", 1)[0]
    return int(text_value) if text_value else 0


def parse_decimal_ratio(value: Any) -> float | None:
    if pd.isna(value):
        return None
    text_value = str(value).strip().replace("%", "").replace(".", "").replace(",", ".")
    if not text_value:
        return None
    return float(text_value) / 100.0


def normalize_section(value: Any, distrito: Any = None) -> tuple[str, str, str]:
    raw = "".join(ch for ch in str(value).strip() if ch.isdigit()).zfill(4)
    distrito_digits = "".join(ch for ch in str(distrito or "").strip() if ch.isdigit())
    cod_distrito = distrito_digits.zfill(2)[-2:] if distrito_digits else raw[:2]
    cod_seccion = raw[-3:]
    return cod_distrito, cod_seccion, f"29070{cod_distrito}{cod_seccion}"


def split_party(value: str) -> tuple[str, str]:
    cleaned = value.strip().strip('"')
    if " - " in cleaned:
        siglas, denominacion = cleaned.split(" - ", 1)
    else:
        siglas, denominacion = cleaned, cleaned
    return siglas.strip().strip('"'), denominacion.strip().strip('"')


def party_alias(siglas: str, denominacion: str) -> tuple[str, str, bool]:
    text = f"{siglas or ''} {denominacion or ''}".upper()

    if any(pattern in text for pattern in LOCAL_PATTERNS):
        return "LOCAL", "LOCAL", True
    if "PSOE" in text or "SOCIALISTA" in text:
        return "PSOE", "LEFT", False
    if re.search(r"(^|[^A-Z])PP([^A-Z]|$)", text) or "PARTIDO POPULAR" in text:
        return "PP", "RIGHT", False
    if "VOX" in text:
        return "VOX", "RIGHT", False
    if re.search(r"(^|[^A-Z])CS([^A-Z]|$)", text) or "CIUDADANOS" in text:
        return "CS", "CENTER", False
    if "PACMA" in text or "ANIMALISTA" in text:
        return "PACMA", "GREEN", False
    if "EQUO" in text or "VERDES" in text or "GRUPO VERDE" in text:
        return "GREEN", "GREEN", False
    if any(pattern in text for pattern in ("ADELANTE ANDALUC", "PODEMOS", "IZQUIERDA UNIDA", "IULV-CA", "SUMAR", "CON ANDALUC", "POR ANDALUC")):
        return "SUMAR_PODEMOS_IU", "LEFT", False
    if re.search(r"(^|[^A-Z])IU([^A-Z]|$)", text):
        return "SUMAR_PODEMOS_IU", "LEFT", False
    return "OTHER", "OTHER", False


def execute_sql_file(conn, relative_path: str) -> None:
    conn.execute(text((PROJECT_ROOT / relative_path).read_text()))


def ensure_model(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts"))
        execute_sql_file(conn, "sql/core/007_create_core_electoral_historical.sql")


def main() -> None:
    args = parse_args()
    resultados_path = find_source_file(
        args.resultados,
        "29070_Mijas_EleccionesAndaluzas2018_UNIFICADO.csv",
    )
    datos_path = find_source_file(args.datos, "Andaluzas_2018_Datos_Mesas.csv")

    engine = create_engine(args.db)
    ensure_model(engine)

    datos_raw = pd.read_csv(datos_path, sep=";", encoding="utf-8-sig")
    resultados_raw = pd.read_csv(resultados_path, sep=";", encoding="utf-8-sig")

    totals_rows = []
    for row in datos_raw.to_dict("records"):
        cod_distrito, cod_seccion, seccion_id = normalize_section(row["seccion"], row.get("distrito"))
        totals_rows.append(
            {
                "election_id": None,
                "anio": 2018,
                "mes": 12,
                "cod_provincia": "29",
                "cod_municipio": "070",
                "cod_distrito": cod_distrito,
                "cod_seccion": cod_seccion,
                "cod_mesa": None,
                "seccion_id": seccion_id,
                "censo": parse_int(row.get("censo")),
                "votos_emitidos": parse_int(row.get("n_votantes")),
                "votos_validos": parse_int(row.get("votos_candidaturas")),
                "votos_blanco": parse_int(row.get("votos_blanco")),
                "votos_nulos": parse_int(row.get("votos_nulos")),
                "votos_candidaturas": parse_int(row.get("votos_candidaturas")),
                "num_mesas": parse_int(row.get("num_mesas")),
                "source_file": datos_path.name,
            }
        )
    totals_df = pd.DataFrame(totals_rows)

    party_lookup: dict[str, dict[str, Any]] = {}
    result_rows = []
    for row in resultados_raw.to_dict("records"):
        cod_distrito, cod_seccion, seccion_id = normalize_section(row["seccion"], 1)
        siglas, denominacion = split_party(str(row["Formación política"]))
        party_key = f"{siglas}||{denominacion}"
        if party_key not in party_lookup:
            cod_candidatura = f"A18{len(party_lookup) + 1:03d}"
            family, bloc, is_local = party_alias(siglas, denominacion)
            party_lookup[party_key] = {
                "cod_candidatura": cod_candidatura,
                "siglas": siglas,
                "denominacion": denominacion,
                "siglas_originales": siglas,
                "denominacion_original": denominacion,
                "normalized_party_family": family,
                "ideological_bloc": bloc,
                "is_local_party": is_local,
            }

        result_rows.append(
            {
                "election_id": None,
                "anio": 2018,
                "mes": 12,
                "cod_provincia": "29",
                "cod_municipio": "070",
                "cod_distrito": cod_distrito,
                "cod_seccion": cod_seccion,
                "cod_mesa": None,
                "seccion_id": seccion_id,
                "cod_candidatura": party_lookup[party_key]["cod_candidatura"],
                "siglas": siglas,
                "denominacion": denominacion,
                "votos": parse_int(row["Votos"]),
                "pct_voto_source": parse_decimal_ratio(row.get("% Votos")),
                "source_file": resultados_path.name,
            }
        )

    candidates_df = pd.DataFrame(party_lookup.values())
    results_df = pd.DataFrame(result_rows)
    section_df = results_df.merge(
        totals_df[
            [
                "seccion_id",
                "censo",
                "votos_emitidos",
                "votos_validos",
                "votos_blanco",
                "votos_nulos",
            ]
        ],
        on="seccion_id",
        how="left",
        validate="many_to_one",
    )
    section_df["pct_voto"] = (
        section_df["votos"] / section_df["votos_validos"].replace({0: pd.NA})
    ).round(6)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO core.election (
                    tipo_eleccion_code,
                    tipo_eleccion_nombre,
                    anio,
                    mes,
                    num_vuelta,
                    election_date,
                    source_folder,
                    source_file
                )
                VALUES (
                    'ANDALUZAS',
                    'Elecciones Andaluzas',
                    2018,
                    12,
                    1,
                    DATE '2018-12-02',
                    'andaluzas',
                    :source_file
                )
                ON CONFLICT (tipo_eleccion_code, anio, mes, COALESCE(num_vuelta, 1))
                DO UPDATE SET
                    tipo_eleccion_nombre = EXCLUDED.tipo_eleccion_nombre,
                    election_date = EXCLUDED.election_date,
                    source_folder = EXCLUDED.source_folder,
                    source_file = EXCLUDED.source_file
                RETURNING election_id
                """
            ),
            {"source_file": f"{datos_path.name};{resultados_path.name}"},
        ).one()
        election_id = int(row.election_id)

        datos_raw.assign(source_file=datos_path.name).to_sql(
            "andaluzas_2018_datos_mesa",
            conn,
            schema="raw",
            if_exists="replace",
            index=False,
        )
        resultados_raw.assign(source_file=resultados_path.name).to_sql(
            "andaluzas_2018_resultados_mesa",
            conn,
            schema="raw",
            if_exists="replace",
            index=False,
        )
        conn.execute(text("ALTER TABLE raw.andaluzas_2018_datos_mesa ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMP DEFAULT NOW()"))
        conn.execute(text("ALTER TABLE raw.andaluzas_2018_resultados_mesa ADD COLUMN IF NOT EXISTS loaded_at TIMESTAMP DEFAULT NOW()"))

        for df in (totals_df, results_df, candidates_df, section_df):
            df["election_id"] = election_id

        totals_df.to_sql(
            "andaluzas_2018_datos_mesa",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        results_df.to_sql(
            "andaluzas_2018_resultados_mesa",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        candidates_df.to_sql(
            "andaluzas_2018_candidates_tmp",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        section_df.to_sql(
            "andaluzas_2018_section_tmp",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )

        conn.execute(text("DELETE FROM core.resultados_seccion WHERE election_id = :election_id"), {"election_id": election_id})
        conn.execute(
            text(
                """
                INSERT INTO core.candidatura (
                    election_id,
                    cod_candidatura,
                    siglas,
                    denominacion,
                    cod_cab_prov,
                    cod_cab_auto,
                    cod_cab_nac
                )
                SELECT
                    election_id,
                    cod_candidatura::char(6),
                    siglas,
                    denominacion,
                    NULL::char(6),
                    NULL::char(6),
                    NULL::char(6)
                FROM staging.andaluzas_2018_candidates_tmp
                ON CONFLICT (election_id, cod_candidatura)
                DO UPDATE SET
                    siglas = EXCLUDED.siglas,
                    denominacion = EXCLUDED.denominacion;

                INSERT INTO core.candidatura_alias (
                    election_id,
                    cod_candidatura,
                    siglas_originales,
                    denominacion_original,
                    normalized_party_family,
                    ideological_bloc,
                    is_local_party
                )
                SELECT
                    election_id,
                    cod_candidatura,
                    siglas_originales,
                    denominacion_original,
                    normalized_party_family,
                    ideological_bloc,
                    is_local_party
                FROM staging.andaluzas_2018_candidates_tmp
                ON CONFLICT (election_id, cod_candidatura)
                DO UPDATE SET
                    siglas_originales = EXCLUDED.siglas_originales,
                    denominacion_original = EXCLUDED.denominacion_original,
                    normalized_party_family = EXCLUDED.normalized_party_family,
                    ideological_bloc = EXCLUDED.ideological_bloc,
                    is_local_party = EXCLUDED.is_local_party;

                INSERT INTO core.resultados_seccion (
                    election_id,
                    seccion_id,
                    anio,
                    mes,
                    tipo_eleccion_code,
                    cod_candidatura,
                    siglas,
                    denominacion,
                    votos_partido,
                    votos_validos,
                    votos_emitidos,
                    votos_blanco,
                    votos_nulos,
                    censo,
                    pct_voto,
                    source_type,
                    source_file
                )
                SELECT
                    election_id,
                    seccion_id,
                    2018,
                    12,
                    'ANDALUZAS',
                    cod_candidatura,
                    siglas,
                    denominacion,
                    votos::bigint,
                    votos_validos::bigint,
                    votos_emitidos::bigint,
                    votos_blanco::bigint,
                    votos_nulos::bigint,
                    censo::bigint,
                    pct_voto::numeric,
                    'ANDALUZAS_SECTION_CSV',
                    source_file
                FROM staging.andaluzas_2018_section_tmp
                ON CONFLICT (election_id, seccion_id, cod_candidatura)
                DO UPDATE SET
                    siglas = EXCLUDED.siglas,
                    denominacion = EXCLUDED.denominacion,
                    votos_partido = EXCLUDED.votos_partido,
                    votos_validos = EXCLUDED.votos_validos,
                    votos_emitidos = EXCLUDED.votos_emitidos,
                    votos_blanco = EXCLUDED.votos_blanco,
                    votos_nulos = EXCLUDED.votos_nulos,
                    censo = EXCLUDED.censo,
                    pct_voto = EXCLUDED.pct_voto,
                    source_type = EXCLUDED.source_type,
                    source_file = EXCLUDED.source_file,
                    updated_at = NOW();
                """
            )
        )

    print(
        "LOADED "
        f"file={datos_path.name}+{resultados_path.name} election_id={election_id} "
        f"type=ANDALUZAS year=2018 month=12 sections={section_df['seccion_id'].nunique()} "
        f"candidates={candidates_df['cod_candidatura'].nunique()} rows={len(section_df)} "
        "grain=section"
    )


if __name__ == "__main__":
    main()
