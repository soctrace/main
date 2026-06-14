from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data/raw/elections/04201905_MESA.zip"
DEFAULT_EXTRACT_DIR = PROJECT_ROOT / "data/raw/elections/04201905_MESA"
DEFAULT_DB = "postgresql:///mijas"
ENCODING = "cp1252"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Mijas 2019 municipal election results.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--cod-provincia", default="29")
    parser.add_argument("--cod-municipio", default="070")
    return parser.parse_args()


def digits(value: str, width: int) -> str:
    return "".join(ch for ch in str(value).strip() if ch.isdigit()).zfill(width)[-width:]


def as_int(value: str) -> int:
    stripped = value.strip()
    return int(stripped) if stripped else 0


def extract_zip(input_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_path) as archive:
        archive.extractall(extract_dir)
    return extract_dir


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding=ENCODING).splitlines()


def parse_candidate(line: str) -> dict[str, Any]:
    return {
        "record_type": "03",
        "raw_line": line,
        "tipo_eleccion": line[0:2],
        "anio": as_int(line[2:6]),
        "mes": as_int(line[6:8]),
        "cod_candidatura": line[8:14],
        "siglas_originales": line[14:64].strip(),
        "denominacion_original": line[64:214].strip(),
        "cod_cab_prov": line[214:220],
        "cod_cab_auto": line[220:226],
        "cod_cab_nac": line[226:232],
    }


def parse_mesa_totals(line: str) -> dict[str, Any]:
    cod_seccion_raw = line[18:22]
    cod_seccion = cod_seccion_raw[:3]
    seccion_id = f"{line[11:13]}{line[13:16]}{line[16:18]}{cod_seccion}"
    return {
        "record_type": "09",
        "raw_line": line,
        "tipo_eleccion": line[0:2],
        "anio": as_int(line[2:6]),
        "mes": as_int(line[6:8]),
        "num_vuelta": as_int(line[8:9]),
        "cod_comunidad": line[9:11],
        "cod_provincia": line[11:13],
        "cod_municipio": line[13:16],
        "cod_distrito": line[16:18],
        "cod_seccion_raw": cod_seccion_raw,
        "cod_seccion": cod_seccion,
        "cod_mesa": line[22:23],
        "seccion_id": seccion_id,
        "censo_ine": as_int(line[23:30]),
        "censo_escrutinio": as_int(line[30:37]),
        "censo_cere": as_int(line[37:44]),
        "votantes_cere": as_int(line[44:51]),
        "votantes_avance1": as_int(line[51:58]),
        "votantes_avance2": as_int(line[58:65]),
        "votos_blanco": as_int(line[65:72]),
        "votos_nulos": as_int(line[72:79]),
        "votos_candidaturas": as_int(line[79:86]),
        "votos_ref_si": as_int(line[86:93]),
        "votos_ref_no": as_int(line[93:100]),
        "datos_oficiales": line[100:101],
    }


def parse_mesa_candidate(line: str) -> dict[str, Any]:
    cod_seccion_raw = line[18:22]
    cod_seccion = cod_seccion_raw[:3]
    seccion_id = f"{line[11:13]}{line[13:16]}{line[16:18]}{cod_seccion}"
    return {
        "record_type": "10",
        "raw_line": line,
        "tipo_eleccion": line[0:2],
        "anio": as_int(line[2:6]),
        "mes": as_int(line[6:8]),
        "num_vuelta": as_int(line[8:9]),
        "cod_comunidad": line[9:11],
        "cod_provincia": line[11:13],
        "cod_municipio": line[13:16],
        "cod_distrito": line[16:18],
        "cod_seccion_raw": cod_seccion_raw,
        "cod_seccion": cod_seccion,
        "cod_mesa": line[22:23],
        "seccion_id": seccion_id,
        "cod_candidatura": line[23:29],
        "votos": as_int(line[29:36]),
    }


def party_alias(siglas: str, denominacion: str) -> tuple[str, str, bool]:
    siglas_upper = siglas.upper()
    denom_upper = denominacion.upper()
    text = f"{siglas_upper} {denom_upper}"

    if siglas_upper in {"PP"} or "PARTIDO POPULAR" in text:
        return "PP", "RIGHT", False
    if siglas_upper in {"PSOE", "PSOE-A"} or "SOCIALISTA" in text:
        return "PSOE", "LEFT", False
    if siglas_upper in {"CS", "CS.", "CIUDADANOS"} or "CIUDADANOS" in text:
        return "CS", "CENTER", False
    if siglas_upper == "VOX":
        return "VOX", "RIGHT", False
    if "PACMA" in text or "ANIMALISTA" in text:
        return "PACMA", "GREEN", False
    if "MVM" in text or "VECINAL" in text or "MIJEÑ" in text or "MIJAS" in text:
        return siglas_upper, "LOCAL", True
    if "ADELANTE" in text or "MAS ANDALUCIA" in text or "MÁS ANDALUCIA" in text:
        return "LEFT_COALITION", "LEFT", False
    if "PODEMOS" in text:
        return "PODEMOS", "LEFT", False
    if "IZQUIERDA UNIDA" in text or siglas_upper.startswith("IU"):
        return "IU", "LEFT", False
    return siglas_upper or "OTHER", "OTHER", False


def load_inputs(extract_dir: Path, cod_provincia: str, cod_municipio: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    target_prov = digits(cod_provincia, 2)
    target_mun = digits(cod_municipio, 3)

    totals = [
        parse_mesa_totals(line)
        for line in read_lines(extract_dir / "09041905.DAT")
        if line[11:13] == target_prov and line[13:16] == target_mun
    ]
    votes = [
        parse_mesa_candidate(line)
        for line in read_lines(extract_dir / "10041905.DAT")
        if line[11:13] == target_prov and line[13:16] == target_mun
    ]
    candidate_codes = {row["cod_candidatura"] for row in votes}
    candidates = [
        parse_candidate(line)
        for line in read_lines(extract_dir / "03041905.DAT")
        if line[8:14] in candidate_codes
    ]

    totals_df = pd.DataFrame(totals)
    votes_df = pd.DataFrame(votes)
    candidates_df = pd.DataFrame(candidates)

    staging_df = votes_df.merge(
        totals_df[
            [
                "cod_provincia",
                "cod_municipio",
                "cod_distrito",
                "cod_seccion",
                "cod_mesa",
                "censo_ine",
                "votos_blanco",
                "votos_nulos",
                "votos_candidaturas",
            ]
        ],
        on=["cod_provincia", "cod_municipio", "cod_distrito", "cod_seccion", "cod_mesa"],
        how="left",
        validate="many_to_one",
    ).merge(
        candidates_df[["cod_candidatura", "siglas_originales"]],
        on="cod_candidatura",
        how="left",
        validate="many_to_one",
    )

    raw_df = pd.concat([candidates_df, totals_df, votes_df], ignore_index=True, sort=False)
    raw_df["source_file"] = raw_df["record_type"].map(
        {"03": "03041905.DAT", "09": "09041905.DAT", "10": "10041905.DAT"}
    )
    raw_df["source_encoding"] = ENCODING

    return raw_df, staging_df, candidates_df, totals_df


def execute_sql_file(conn, relative_path: str) -> None:
    sql = (PROJECT_ROOT / relative_path).read_text()
    conn.execute(text(sql))


def ensure_database(engine) -> int:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts"))
        for path in [
            "sql/raw/003_create_raw_elecciones_municipales_2019_mesa.sql",
            "sql/staging/004_create_staging_resultados_mesa_2019.sql",
            "sql/core/004_create_core_candidatura_alias.sql",
            "sql/core/005_create_core_elecciones_mun_2019.sql",
        ]:
            execute_sql_file(conn, path)
        row = conn.execute(
            text(
                """
                INSERT INTO core.election_type (tipo_eleccion_code, descripcion)
                VALUES ('04', 'Elecciones Municipales')
                ON CONFLICT (tipo_eleccion_code) DO NOTHING;

                INSERT INTO core.election (
                    tipo_eleccion_code,
                    anio,
                    mes,
                    num_vuelta
                )
                VALUES ('04', 2019, 5, 1)
                ON CONFLICT (tipo_eleccion_code, anio, mes, num_vuelta)
                DO UPDATE SET mes = EXCLUDED.mes
                RETURNING election_id;
                """
            )
        ).first()
    return int(row[0])


def replace_table(engine, df: pd.DataFrame, schema: str, table: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {schema}.{table}"))
    df.to_sql(table, engine, schema=schema, if_exists="append", index=False)


def load_raw_and_staging(
    engine,
    raw_df: pd.DataFrame,
    staging_df: pd.DataFrame,
    election_id: int,
) -> pd.DataFrame:
    raw_columns = [
        "record_type",
        "raw_line",
        "tipo_eleccion",
        "anio",
        "mes",
        "num_vuelta",
        "cod_comunidad",
        "cod_provincia",
        "cod_municipio",
        "cod_distrito",
        "cod_seccion_raw",
        "cod_seccion",
        "cod_mesa",
        "seccion_id",
        "cod_candidatura",
        "siglas_originales",
        "denominacion_original",
        "cod_cab_prov",
        "cod_cab_auto",
        "cod_cab_nac",
        "censo_ine",
        "censo_escrutinio",
        "censo_cere",
        "votantes_cere",
        "votantes_avance1",
        "votantes_avance2",
        "votos_blanco",
        "votos_nulos",
        "votos_candidaturas",
        "votos_ref_si",
        "votos_ref_no",
        "votos",
        "datos_oficiales",
        "source_file",
        "source_encoding",
    ]
    replace_table(
        engine,
        raw_df.reindex(columns=raw_columns).where(pd.notna(raw_df), None),
        "raw",
        "elecciones_municipales_2019_mesa",
    )

    normalized = pd.DataFrame(
        {
            "election_id": election_id,
            "anio": 2019,
            "cod_provincia": staging_df["cod_provincia"].astype(int),
            "cod_municipio": staging_df["cod_municipio"].astype(int),
            "cod_distrito": staging_df["cod_distrito"].astype(int),
            "cod_seccion": staging_df["cod_seccion"],
            "cod_mesa": staging_df["cod_mesa"],
            "seccion_id": staging_df["seccion_id"],
            "cod_candidatura": staging_df["cod_candidatura"],
            "siglas_originales": staging_df["siglas_originales"],
            "votos": staging_df["votos"].astype(int),
            "censo": staging_df["censo_ine"].astype(int),
            "votos_emitidos": (
                staging_df["votos_candidaturas"] + staging_df["votos_blanco"] + staging_df["votos_nulos"]
            ).astype(int),
            "votos_validos": staging_df["votos_candidaturas"].astype(int),
            "votos_blanco": staging_df["votos_blanco"].astype(int),
            "votos_nulos": staging_df["votos_nulos"].astype(int),
            "source_file": "04201905_MESA.zip",
        }
    )
    replace_table(engine, normalized, "staging", "resultados_mesa_2019")
    return normalized


def upsert_core(engine, candidates_df: pd.DataFrame, staging_df: pd.DataFrame, election_id: int) -> None:
    alias_rows = []
    for row in candidates_df.to_dict("records"):
        family, bloc, is_local = party_alias(row["siglas_originales"], row["denominacion_original"])
        alias_rows.append(
            {
                "election_id": election_id,
                "cod_candidatura": row["cod_candidatura"],
                "siglas_originales": row["siglas_originales"],
                "denominacion_original": row["denominacion_original"],
                "normalized_party_family": family,
                "ideological_bloc": bloc,
                "is_local_party": is_local,
            }
        )
    alias_df = pd.DataFrame(alias_rows)

    candidate_core = candidates_df[
        [
            "cod_candidatura",
            "siglas_originales",
            "denominacion_original",
            "cod_cab_prov",
            "cod_cab_auto",
            "cod_cab_nac",
        ]
    ].rename(columns={"siglas_originales": "siglas", "denominacion_original": "denominacion"})
    candidate_core.insert(0, "election_id", election_id)

    with engine.begin() as conn:
        candidate_core.to_sql("candidatura_load_tmp", conn, schema="staging", if_exists="replace", index=False)
        alias_df.to_sql("candidatura_alias_load_tmp", conn, schema="staging", if_exists="replace", index=False)

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
                    cod_candidatura,
                    siglas,
                    denominacion,
                    cod_cab_prov,
                    cod_cab_auto,
                    cod_cab_nac
                FROM staging.candidatura_load_tmp
                ON CONFLICT (election_id, cod_candidatura)
                DO UPDATE SET
                    siglas = EXCLUDED.siglas,
                    denominacion = EXCLUDED.denominacion,
                    cod_cab_prov = EXCLUDED.cod_cab_prov,
                    cod_cab_auto = EXCLUDED.cod_cab_auto,
                    cod_cab_nac = EXCLUDED.cod_cab_nac;

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
                FROM staging.candidatura_alias_load_tmp
                ON CONFLICT (election_id, cod_candidatura)
                DO UPDATE SET
                    siglas_originales = EXCLUDED.siglas_originales,
                    denominacion_original = EXCLUDED.denominacion_original,
                    normalized_party_family = EXCLUDED.normalized_party_family,
                    ideological_bloc = EXCLUDED.ideological_bloc,
                    is_local_party = EXCLUDED.is_local_party;

                INSERT INTO core.mesa (
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa
                )
                SELECT DISTINCT
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa
                FROM staging.resultados_mesa_2019
                ON CONFLICT DO NOTHING;

                INSERT INTO core.datos_mesa (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
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
                    datos_oficiales
                )
                SELECT DISTINCT
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    censo,
                    censo,
                    0,
                    0,
                    NULL::integer,
                    NULL::integer,
                    votos_blanco,
                    votos_nulos,
                    votos_validos,
                    0,
                    0,
                    'S'
                FROM staging.resultados_mesa_2019
                ON CONFLICT (election_id, cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa)
                DO UPDATE SET
                    censo_ine = EXCLUDED.censo_ine,
                    censo_escrutinio = EXCLUDED.censo_escrutinio,
                    censo_cere = EXCLUDED.censo_cere,
                    votantes_cere = EXCLUDED.votantes_cere,
                    votos_blanco = EXCLUDED.votos_blanco,
                    votos_nulos = EXCLUDED.votos_nulos,
                    votos_candidaturas = EXCLUDED.votos_candidaturas,
                    datos_oficiales = EXCLUDED.datos_oficiales;

                INSERT INTO core.resultados_mesa (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    cod_candidatura,
                    votos
                )
                SELECT
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    cod_candidatura,
                    votos
                FROM staging.resultados_mesa_2019
                ON CONFLICT (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    cod_candidatura
                )
                DO UPDATE SET votos = EXCLUDED.votos;

                DROP TABLE IF EXISTS staging.candidatura_load_tmp;
                DROP TABLE IF EXISTS staging.candidatura_alias_load_tmp;
                """
            )
        )


def build_section_aggregate(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE core.elecciones_mun_2019"))
        conn.execute(
            text(
                """
                INSERT INTO core.elecciones_mun_2019 (
                    seccion_id,
                    anio,
                    election_id,
                    cod_candidatura,
                    partido,
                    votos_partido,
                    votos_validos,
                    votos_emitidos,
                    votos_blanco,
                    votos_nulos,
                    censo,
                    pct_voto
                )
                WITH totals AS (
                    SELECT
                        seccion_id,
                        anio,
                        election_id,
                        SUM(censo) AS censo,
                        SUM(votos_emitidos) AS votos_emitidos,
                        SUM(votos_validos) AS votos_validos,
                        SUM(votos_blanco) AS votos_blanco,
                        SUM(votos_nulos) AS votos_nulos
                    FROM (
                        SELECT DISTINCT
                            seccion_id,
                            anio,
                            election_id,
                            cod_provincia,
                            cod_municipio,
                            cod_distrito,
                            cod_seccion,
                            cod_mesa,
                            censo,
                            votos_emitidos,
                            votos_validos,
                            votos_blanco,
                            votos_nulos
                        FROM staging.resultados_mesa_2019
                    ) m
                    GROUP BY seccion_id, anio, election_id
                ),
                party_votes AS (
                    SELECT
                        seccion_id,
                        anio,
                        election_id,
                        cod_candidatura,
                        SUM(votos) AS votos_partido
                    FROM staging.resultados_mesa_2019
                    GROUP BY seccion_id, anio, election_id, cod_candidatura
                )
                SELECT
                    pv.seccion_id,
                    pv.anio,
                    pv.election_id,
                    pv.cod_candidatura,
                    COALESCE(a.normalized_party_family, c.siglas) AS partido,
                    pv.votos_partido,
                    t.votos_validos,
                    t.votos_emitidos,
                    t.votos_blanco,
                    t.votos_nulos,
                    t.censo,
                    ROUND(
                        CASE
                            WHEN t.votos_validos > 0
                            THEN pv.votos_partido::numeric * 100.0 / t.votos_validos
                            ELSE NULL
                        END,
                        6
                    ) AS pct_voto
                FROM party_votes pv
                JOIN totals t
                  ON t.seccion_id = pv.seccion_id
                 AND t.anio = pv.anio
                 AND t.election_id = pv.election_id
                LEFT JOIN core.candidatura c
                  ON c.election_id = pv.election_id
                 AND c.cod_candidatura = pv.cod_candidatura
                LEFT JOIN core.candidatura_alias a
                  ON a.election_id = pv.election_id
                 AND a.cod_candidatura = pv.cod_candidatura;
                """
            )
        )


def refresh_marts(engine) -> None:
    with engine.begin() as conn:
        # v_resultados_seccion_anio is already multi-year over core election tables.
        # Recreating it uses CASCADE in the checked-in SQL and drops dependent marts,
        # so this loader only rebuilds the electoral behavior mart.
        execute_sql_file(conn, "sql/marts/010_mv_electoral_behavior.sql")


def main() -> None:
    args = parse_args()
    extract_dir = extract_zip(args.input, args.extract_dir)
    raw_df, staging_input_df, candidates_df, totals_df = load_inputs(
        extract_dir,
        args.cod_provincia,
        args.cod_municipio,
    )

    if totals_df.empty or staging_input_df.empty:
        raise RuntimeError("No Mijas mesa results found in the election files.")

    engine = create_engine(args.db)
    election_id = ensure_database(engine)
    staging_df = load_raw_and_staging(engine, raw_df, staging_input_df, election_id)
    upsert_core(engine, candidates_df, staging_df, election_id)
    build_section_aggregate(engine)
    refresh_marts(engine)

    print("Municipal 2019 election load completed")
    print(f"- election_id: {election_id}")
    print(f"- raw rows loaded: {len(raw_df)}")
    print(f"- Mijas mesas: {totals_df[['seccion_id', 'cod_mesa']].drop_duplicates().shape[0]}")
    print(f"- Mijas sections: {totals_df['seccion_id'].nunique()}")
    print(f"- mesa-candidacy rows: {len(staging_df)}")
    print(f"- candidacies detected: {len(candidates_df)}")
    print(f"- seccion_id range: {totals_df['seccion_id'].min()} - {totals_df['seccion_id'].max()}")
    print("- candidacy normalization:")
    for row in candidates_df.sort_values("cod_candidatura").to_dict("records"):
        family, bloc, is_local = party_alias(row["siglas_originales"], row["denominacion_original"])
        print(
            f"  {row['cod_candidatura']} {row['siglas_originales']} -> "
            f"{family} / {bloc} / local={is_local}"
        )


if __name__ == "__main__":
    main()
