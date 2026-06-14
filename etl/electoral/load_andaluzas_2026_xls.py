from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = "postgresql:///mijas"
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data/raw/elections/andaluzas/2026"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data/processed/elections/andaluzas/2026"
ELECTION_DATE = "2026-05-17"
ELECTION_YEAR = 2026
ELECTION_MONTH = 5
MIJAS_COD_MUN = 70

PARTY_COLUMNS = [
    "PACMA",
    "PCPA",
    "ADELANTE ANDALUCÍA",
    "FE de las JONS",
    "VOX",
    "PARTIDO AUTÓNOMOS",
    "ANDALUCISTAS-PA",
    "PP",
    "PorA",
    "CONECTA",
    "ESCAÑOS EN BLANCO",
    "SOCIEDAD UNIDA",
    "SALF",
    "PSOE-A",
    "MUNDO+JUSTO",
    "29",
    "NA",
]

PARTY_ALIAS = {
    "PP": ("PP", "RIGHT", False),
    "PSOE-A": ("PSOE", "LEFT", False),
    "VOX": ("VOX", "RIGHT", False),
    "ADELANTE ANDALUCIA": ("ADELANTE_ANDALUCIA", "LEFT", False),
    "PACMA": ("PACMA", "GREEN", False),
    "PCPA": ("PCPA", "LEFT", False),
    "FE DE LAS JONS": ("FAR_RIGHT", "RIGHT", False),
    "ANDALUCISTAS-PA": ("ANDALUSIAN_REGIONAL", "REGIONAL", False),
    "PORA": ("REGIONAL_OR_OTHER", "REGIONAL", False),
    "ESCANOS EN BLANCO": ("BLANK_SEATS", "OTHER", False),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Mijas Andalusian 2026 XLS results.")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--skip-marts-refresh", action="store_true")
    return parser.parse_args()


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )


def find_source_file(explicit: Path | None) -> Path:
    if explicit:
        return explicit

    for candidate in DEFAULT_SOURCE_DIR.glob("*.xls"):
        normalized = strip_accents(candidate.name).lower()
        if "malaga" in normalized and normalized.startswith("resultados"):
            return candidate

    raise FileNotFoundError(f"Could not find Malaga XLS in {DEFAULT_SOURCE_DIR}")


def parse_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text_value = str(value).strip().replace(".", "")
    if "," in text_value:
        text_value = text_value.split(",", 1)[0]
    return int(float(text_value)) if text_value else 0


def clean_codmun(value: Any) -> int | None:
    if pd.isna(value):
        return None
    return int(float(str(value).strip()))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: str(column).strip() for column in df.columns}
    return df.rename(columns=renamed)


def parse_mesa(value: Any) -> tuple[str, str, str]:
    raw = str(value).strip()
    match = re.fullmatch(r"(\d+)-(\d+)-([A-Za-z0-9]+)", raw)
    if not match:
        raise ValueError(f"Unexpected Mesa format: {raw!r}")
    cod_distrito = match.group(1).zfill(2)
    cod_seccion = match.group(2).zfill(3)
    cod_mesa = match.group(3).upper()
    return cod_distrito, cod_seccion, cod_mesa


def seccion_id(cod_municipio: Any, cod_distrito: str, cod_seccion: str) -> str:
    return f"29{int(cod_municipio):03d}{cod_distrito}{cod_seccion}"


def stable_candidate_code(position: int) -> str:
    # core.candidatura.cod_candidatura is char(6) in the current model.
    return f"A26{position:03d}"


def alias_for(siglas: str) -> tuple[str, str, bool]:
    key = strip_accents(siglas).upper()
    if key in PARTY_ALIAS:
        return PARTY_ALIAS[key]
    return "OTHER", "OTHER", False


def execute_sql_file(conn, relative_path: str) -> None:
    conn.execute(text((PROJECT_ROOT / relative_path).read_text()))


def ensure_model(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts"))
        execute_sql_file(conn, "sql/core/004_create_core_candidatura_alias.sql")
        execute_sql_file(conn, "sql/core/007_create_core_electoral_historical.sql")


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    return {
        sheet: normalize_columns(pd.read_excel(path, sheet_name=sheet))
        for sheet in pd.ExcelFile(path).sheet_names
    }


def filter_mijas(df: pd.DataFrame) -> pd.DataFrame:
    if "Codmun" not in df.columns:
        return df.iloc[0:0].copy()
    mask = df["Codmun"].map(clean_codmun).eq(MIJAS_COD_MUN)
    return df.loc[mask].copy()


def build_candidates() -> pd.DataFrame:
    rows = []
    for index, siglas in enumerate(PARTY_COLUMNS, start=1):
        family, bloc, is_local = alias_for(siglas)
        rows.append(
            {
                "cod_candidatura": stable_candidate_code(index),
                "siglas": siglas,
                "denominacion": siglas,
                "siglas_originales": siglas,
                "denominacion_original": siglas,
                "normalized_party_family": family,
                "ideological_bloc": bloc,
                "is_local_party": is_local,
            }
        )
    return pd.DataFrame(rows)


def build_staging(mesas_mijas: pd.DataFrame, candidates_df: pd.DataFrame, source_file: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    totals_rows = []
    result_rows = []
    candidate_by_siglas = candidates_df.set_index("siglas").to_dict("index")

    for row in mesas_mijas.to_dict("records"):
        cod_distrito, cod_seccion, cod_mesa = parse_mesa(row["Mesa"])
        section_id = seccion_id(row["Codmun"], cod_distrito, cod_seccion)
        censo_total = parse_int(row.get("Censo Total"))
        votos_emitidos = parse_int(row.get("Votos Totales"))
        votos_nulos = parse_int(row.get("Votos Nulos"))
        votos_blanco = parse_int(row.get("Votos Blancos"))
        votos_validos = votos_emitidos - votos_nulos

        total_row = {
            "anio": ELECTION_YEAR,
            "mes": ELECTION_MONTH,
            "cod_provincia": "29",
            "cod_municipio": "070",
            "cod_distrito": cod_distrito,
            "cod_seccion": cod_seccion,
            "cod_mesa": cod_mesa,
            "seccion_id": section_id,
            "municipio": row.get("Municipio"),
            "censo": censo_total,
            "censo_total": censo_total,
            "votos_electores": parse_int(row.get("Votos Electores")),
            "votos_interventores": parse_int(row.get("Votos Interventores")),
            "votos_emitidos": votos_emitidos,
            "votos_nulos": votos_nulos,
            "votos_blanco": votos_blanco,
            "votos_validos": votos_validos,
            "source_file": source_file,
        }
        totals_rows.append(total_row)

        for siglas in PARTY_COLUMNS:
            candidate = candidate_by_siglas[siglas]
            result_rows.append(
                {
                    **total_row,
                    "cod_candidatura": candidate["cod_candidatura"],
                    "siglas": siglas,
                    "denominacion": siglas,
                    "votos": parse_int(row.get(siglas)),
                }
            )

    return pd.DataFrame(totals_rows), pd.DataFrame(result_rows)


def build_validation_report(
    totals_df: pd.DataFrame,
    results_df: pd.DataFrame,
    municipios_mijas: pd.DataFrame,
) -> pd.DataFrame:
    if municipios_mijas.empty:
        return pd.DataFrame(
            [{"campo": "Mijas row", "total_secciones": None, "total_municipio": None, "diferencia": None, "ok": False}]
        )

    municipality = municipios_mijas.iloc[0]
    section_totals = totals_df[["censo", "votos_emitidos", "votos_nulos", "votos_blanco", "votos_validos"]]

    rows = [
        ("Censo Total", int(section_totals["censo"].sum()), parse_int(municipality.get("Censo Total"))),
        ("Votos Totales", int(section_totals["votos_emitidos"].sum()), parse_int(municipality.get("Votos Totales"))),
        ("Votos Nulos", int(section_totals["votos_nulos"].sum()), parse_int(municipality.get("Votos Nulos"))),
        ("Votos Blancos", int(section_totals["votos_blanco"].sum()), parse_int(municipality.get("Votos Blancos"))),
        ("Votos Válidos", int(section_totals["votos_validos"].sum()), parse_int(municipality.get("Votos Válidos"))),
    ]

    for siglas in PARTY_COLUMNS:
        rows.append(
            (
                siglas,
                int(results_df.loc[results_df["siglas"].eq(siglas), "votos"].sum()),
                parse_int(municipality.get(siglas)),
            )
        )

    return pd.DataFrame(
        [
            {
                "campo": campo,
                "total_secciones": total_secciones,
                "total_municipio": total_municipio,
                "diferencia": total_secciones - total_municipio,
                "ok": total_secciones == total_municipio,
            }
            for campo, total_secciones, total_municipio in rows
        ]
    )


def refresh_marts(engine) -> None:
    with engine.begin() as conn:
        execute_sql_file(conn, "sql/marts/018_v_resultados_seccion_eleccion.sql")
        execute_sql_file(conn, "sql/marts/010_mv_electoral_behavior.sql")
        execute_sql_file(conn, "sql/marts/019_ml_electoral_section_panel.sql")


def main() -> None:
    args = parse_args()
    source_path = find_source_file(args.source)
    source_file = source_path.name
    workbook = read_workbook(source_path)
    engine = create_engine(args.db)
    ensure_model(engine)

    mesas = workbook["Mesas"]
    municipios = workbook["Municipios"]
    mesas_sin_escrutar = workbook["MesasSinEscrutar"]
    mesas_mijas = filter_mijas(mesas)
    municipios_mijas = filter_mijas(municipios)
    pending_mijas = filter_mijas(mesas_sin_escrutar)
    candidates_df = build_candidates()
    totals_df, staging_df = build_staging(mesas_mijas, candidates_df, source_file)
    validation_df = build_validation_report(totals_df, staging_df, municipios_mijas)

    section_totals = totals_df.groupby(
        ["seccion_id", "cod_distrito", "cod_seccion"], as_index=False
    ).agg(
        censo=("censo", "sum"),
        votos_emitidos=("votos_emitidos", "sum"),
        votos_validos=("votos_validos", "sum"),
        votos_blanco=("votos_blanco", "sum"),
        votos_nulos=("votos_nulos", "sum"),
    )
    section_votes = staging_df.groupby(
        ["seccion_id", "cod_candidatura", "siglas", "denominacion"], as_index=False
    ).agg(votos_partido=("votos", "sum"))
    section_df = section_votes.merge(section_totals, on="seccion_id", how="left", validate="many_to_one")
    section_df["pct_voto"] = (
        section_df["votos_partido"] / section_df["votos_validos"].replace({0: pd.NA})
    ).round(6)
    section_df["source_file"] = source_file

    args.report_dir.mkdir(parents=True, exist_ok=True)
    validation_path = args.report_dir / "andaluzas_2026_mijas_validation.csv"
    audit_path = args.report_dir / "andaluzas_2026_mijas_audit.txt"
    validation_df.to_csv(validation_path, index=False)
    audit_path.write_text(
        "\n".join(
            [
                f"source_file={source_file}",
                f"sheets={list(workbook)}",
                f"mesas_rows={len(mesas)}",
                f"mijas_mesas={len(mesas_mijas)}",
                f"mijas_sections={totals_df['seccion_id'].nunique()}",
                f"mesa_rule=Mesa '<distrito>-<seccion>-<mesa>', example 1-001-A => distrito 01, seccion 001, mesa A",
                f"mijas_pending_tables={len(pending_mijas)}",
                f"party_columns={PARTY_COLUMNS}",
                f"municipality_validation_all_ok={bool(validation_df['ok'].all())}",
                "election_date=2026-05-17 (Junta Electoral de Andalucía calendar)",
            ]
        ),
        encoding="utf-8",
    )

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
                    :anio,
                    :mes,
                    1,
                    CAST(:election_date AS date),
                    'andaluzas/2026',
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
            {
                "anio": ELECTION_YEAR,
                "mes": ELECTION_MONTH,
                "election_date": ELECTION_DATE,
                "source_file": source_file,
            },
        ).one()
        election_id = int(row.election_id)

        loaded_at = pd.Timestamp.utcnow().tz_localize(None)
        for table_name, sheet_name, df in [
            ("andaluzas_2026_resultados_malaga", "Mesas", mesas),
            ("andaluzas_2026_municipios_malaga", "Municipios", municipios),
            ("andaluzas_2026_mesas_sin_escrutar_malaga", "MesasSinEscrutar", mesas_sin_escrutar),
        ]:
            raw_df = df.copy()
            raw_df["source_file"] = source_file
            raw_df["sheet_name"] = sheet_name
            raw_df["loaded_at"] = loaded_at
            raw_df.to_sql(table_name, conn, schema="raw", if_exists="replace", index=False)

        for df in (totals_df, staging_df, candidates_df, section_df):
            df.insert(0, "election_id", election_id)
            df["loaded_at"] = loaded_at

        staging_df.to_sql(
            "andaluzas_2026_resultados_mesa",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        validation_db_df = validation_df.copy()
        validation_db_df["election_id"] = election_id
        validation_db_df["source_file"] = source_file
        validation_db_df["loaded_at"] = loaded_at
        validation_db_df.to_sql(
            "andaluzas_2026_validation_mijas",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        candidates_df.to_sql(
            "andaluzas_2026_candidates_tmp",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        totals_df.to_sql(
            "andaluzas_2026_totals_tmp",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )
        section_df.to_sql(
            "andaluzas_2026_section_tmp",
            conn,
            schema="staging",
            if_exists="replace",
            index=False,
        )

        conn.execute(
            text(
                """
                DELETE FROM core.resultados_seccion WHERE election_id = :election_id;
                DELETE FROM core.resultados_mesa WHERE election_id = :election_id;
                DELETE FROM core.datos_mesa WHERE election_id = :election_id;

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
                FROM staging.andaluzas_2026_candidates_tmp
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
                FROM staging.andaluzas_2026_candidates_tmp
                ON CONFLICT (election_id, cod_candidatura)
                DO UPDATE SET
                    siglas_originales = EXCLUDED.siglas_originales,
                    denominacion_original = EXCLUDED.denominacion_original,
                    normalized_party_family = EXCLUDED.normalized_party_family,
                    ideological_bloc = EXCLUDED.ideological_bloc,
                    is_local_party = EXCLUDED.is_local_party;

                INSERT INTO core.seccion (
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    geom
                )
                SELECT DISTINCT
                    t.cod_provincia::smallint,
                    t.cod_municipio::smallint,
                    t.cod_distrito::smallint,
                    t.cod_seccion::char(3),
                    h.geom
                FROM staging.andaluzas_2026_totals_tmp t
                LEFT JOIN core.seccion_historica h
                  ON h.anio = :anio
                 AND h.seccion_id = t.seccion_id
                ON CONFLICT (cod_provincia, cod_municipio, cod_distrito, cod_seccion)
                DO UPDATE SET
                    geom = COALESCE(core.seccion.geom, EXCLUDED.geom);

                INSERT INTO core.mesa (
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa
                )
                SELECT DISTINCT
                    cod_provincia::smallint,
                    cod_municipio::smallint,
                    cod_distrito::smallint,
                    cod_seccion::char(3),
                    cod_mesa::char(1)
                FROM staging.andaluzas_2026_totals_tmp
                ON CONFLICT DO NOTHING;

                INSERT INTO core.datos_mesa (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    seccion_id,
                    censo_ine,
                    censo_escrutinio,
                    censo_cere,
                    votantes_cere,
                    votantes_avance1,
                    votantes_avance2,
                    votos_blanco,
                    votos_nulos,
                    votos_candidaturas,
                    votos_ref_si,
                    votos_ref_no,
                    datos_oficiales,
                    censo,
                    votos_emitidos,
                    votos_validos,
                    source_file,
                    loaded_at
                )
                SELECT DISTINCT
                    election_id,
                    cod_provincia::smallint,
                    cod_municipio::smallint,
                    cod_distrito::smallint,
                    cod_seccion::char(3),
                    cod_mesa::char(1),
                    seccion_id,
                    censo::integer,
                    censo::integer,
                    0::integer,
                    0::integer,
                    NULL::integer,
                    NULL::integer,
                    votos_blanco::integer,
                    votos_nulos::integer,
                    (votos_validos - votos_blanco)::integer,
                    NULL::integer,
                    NULL::integer,
                    'S'::char(1),
                    censo::bigint,
                    votos_emitidos::bigint,
                    votos_validos::bigint,
                    source_file,
                    loaded_at
                FROM staging.andaluzas_2026_totals_tmp;

                INSERT INTO core.resultados_mesa (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    seccion_id,
                    cod_candidatura,
                    votos,
                    source_file,
                    loaded_at
                )
                SELECT
                    election_id,
                    cod_provincia::smallint,
                    cod_municipio::smallint,
                    cod_distrito::smallint,
                    cod_seccion::char(3),
                    cod_mesa::char(1),
                    seccion_id,
                    cod_candidatura::char(6),
                    votos::integer,
                    source_file,
                    loaded_at
                FROM staging.andaluzas_2026_resultados_mesa;

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
                    :anio,
                    :mes,
                    'ANDALUZAS',
                    cod_candidatura,
                    siglas,
                    denominacion,
                    votos_partido::bigint,
                    votos_validos::bigint,
                    votos_emitidos::bigint,
                    votos_blanco::bigint,
                    votos_nulos::bigint,
                    censo::bigint,
                    pct_voto::numeric,
                    'ANDALUZAS_2026_XLS',
                    source_file
                FROM staging.andaluzas_2026_section_tmp
                ON CONFLICT (election_id, seccion_id, cod_candidatura)
                DO UPDATE SET
                    anio = EXCLUDED.anio,
                    mes = EXCLUDED.mes,
                    tipo_eleccion_code = EXCLUDED.tipo_eleccion_code,
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
            ),
            {"election_id": election_id, "anio": ELECTION_YEAR, "mes": ELECTION_MONTH},
        )

    if not args.skip_marts_refresh:
        refresh_marts(engine)

    other_parties = candidates_df.loc[
        candidates_df["normalized_party_family"].eq("OTHER"), "siglas"
    ].tolist()
    print(
        "LOADED "
        f"file={source_file} election_id={election_id} type=ANDALUZAS "
        f"year={ELECTION_YEAR} month={ELECTION_MONTH} election_date={ELECTION_DATE} "
        f"mijas_mesas={len(mesas_mijas)} sections={totals_df['seccion_id'].nunique()} "
        f"candidates={candidates_df['cod_candidatura'].nunique()} rows={len(staging_df)} "
        f"pending_mijas={len(pending_mijas)} validation_ok={bool(validation_df['ok'].all())} "
        f"validation_report={validation_path} audit_report={audit_path} "
        f"other_pending={other_parties}"
    )


if __name__ == "__main__":
    main()
