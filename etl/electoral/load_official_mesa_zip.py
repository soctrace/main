from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = "postgresql:///mijas"
ENCODING = "cp1252"
TARGET_PROVINCE = "29"
TARGET_MUNICIPALITY = "070"

TYPE_MAP = {
    "02": ("CONGRESO", "Elecciones al Congreso de los Diputados"),
    "04": ("MUNICIPALES", "Elecciones Municipales"),
    "07": ("PARLAMENTO_EUROPEO", "Elecciones al Parlamento Europeo"),
}

KNOWN_DATES = {
    ("CONGRESO", 2019, 4): "2019-04-28",
    ("CONGRESO", 2019, 11): "2019-11-10",
    ("CONGRESO", 2023, 7): "2023-07-23",
    ("MUNICIPALES", 2015, 5): "2015-05-24",
    ("MUNICIPALES", 2019, 5): "2019-05-26",
    ("MUNICIPALES", 2023, 5): "2023-05-28",
    ("PARLAMENTO_EUROPEO", 2014, 5): "2014-05-25",
    ("PARLAMENTO_EUROPEO", 2019, 5): "2019-05-26",
    ("PARLAMENTO_EUROPEO", 2024, 6): "2024-06-09",
}

LOCAL_PATTERNS = (
    "POR MI PUEBLO",
    "SOYDEMIJAS",
    "SOY DE MIJAS",
    "A.MIJAS",
    "A.MIHA",
    "ALTERNATIVA MIJE",
)


@dataclass(frozen=True)
class ElectionZip:
    path: Path
    official_type: str
    tipo_eleccion_code: str
    tipo_eleccion_nombre: str
    anio: int
    mes: int
    granularidad: str

    @property
    def stem_code(self) -> str:
        return f"{self.official_type}{self.anio % 100:02d}{self.mes:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Mijas official mesa-level election ZIPs.")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "data/raw/elections")
    parser.add_argument(
        "--folders",
        nargs="*",
        default=["congreso", "municipales", "parlamento_europeo"],
        help="Election source folders under data/raw/elections.",
    )
    return parser.parse_args()


def digits(value: Any, width: int) -> str:
    return "".join(ch for ch in str(value).strip() if ch.isdigit()).zfill(width)[-width:]


def as_int(value: str | None) -> int:
    stripped = (value or "").strip()
    return int(stripped) if stripped else 0


def parse_zip_name(path: Path) -> ElectionZip | None:
    match = re.fullmatch(r"(?P<tipo>\d{2})(?P<anio>\d{4})(?P<mes>\d{2})_(?P<granularidad>[A-Z]+)\.zip", path.name)
    if not match:
        print(f"SKIP filename_not_recognized {path}")
        return None

    official_type = match.group("tipo")
    if official_type not in TYPE_MAP:
        print(f"SKIP unsupported_election_type official_type={official_type} file={path}")
        return None

    granularidad = match.group("granularidad")
    if granularidad != "MESA":
        print(f"SKIP unsupported_granularity granularidad={granularidad} file={path}")
        return None

    tipo_eleccion_code, tipo_eleccion_nombre = TYPE_MAP[official_type]
    return ElectionZip(
        path=path,
        official_type=official_type,
        tipo_eleccion_code=tipo_eleccion_code,
        tipo_eleccion_nombre=tipo_eleccion_nombre,
        anio=int(match.group("anio")),
        mes=int(match.group("mes")),
        granularidad=granularidad,
    )


def read_zip_lines(archive: zipfile.ZipFile, filename: str) -> list[str]:
    with archive.open(filename) as handle:
        return handle.read().decode(ENCODING, errors="replace").splitlines()


def parse_candidate(line: str) -> dict[str, Any]:
    return {
        "cod_candidatura": line[8:14],
        "siglas": line[14:64].strip(),
        "denominacion": line[64:214].strip(),
        "cod_cab_prov": line[214:220].strip() or None,
        "cod_cab_auto": line[220:226].strip() or None,
        "cod_cab_nac": line[226:232].strip() or None,
    }


def mesa_keys(line: str) -> dict[str, Any]:
    cod_provincia = line[11:13]
    cod_municipio = line[13:16]
    cod_distrito = line[16:18]
    cod_seccion = line[18:22][:3]
    cod_mesa = line[22:23]
    seccion_id = f"{cod_provincia}{cod_municipio}{cod_distrito}{cod_seccion}"
    return {
        "cod_provincia": int(cod_provincia),
        "cod_municipio": int(cod_municipio),
        "cod_distrito": int(cod_distrito),
        "cod_seccion": cod_seccion,
        "cod_mesa": cod_mesa,
        "seccion_id": seccion_id,
    }


def parse_mesa_totals(line: str, source_file: str) -> dict[str, Any]:
    row = mesa_keys(line)
    votos_blanco = as_int(line[65:72])
    votos_nulos = as_int(line[72:79])
    votos_candidaturas = as_int(line[79:86])
    row.update(
        {
            "censo_ine": as_int(line[23:30]),
            "censo_escrutinio": as_int(line[30:37]),
            "censo_cere": as_int(line[37:44]),
            "votantes_cere": as_int(line[44:51]),
            "votantes_avance1": as_int(line[51:58]) or None,
            "votantes_avance2": as_int(line[58:65]) or None,
            "votos_blanco": votos_blanco,
            "votos_nulos": votos_nulos,
            "votos_candidaturas": votos_candidaturas,
            "votos_ref_si": as_int(line[86:93]),
            "votos_ref_no": as_int(line[93:100]),
            "datos_oficiales": (line[100:101] or "S").strip() or "S",
            "censo": as_int(line[23:30]),
            "votos_emitidos": votos_candidaturas + votos_blanco + votos_nulos,
            "votos_validos": votos_candidaturas,
            "source_file": source_file,
        }
    )
    return row


def parse_mesa_result(line: str, source_file: str) -> dict[str, Any]:
    row = mesa_keys(line)
    row.update(
        {
            "cod_candidatura": line[23:29],
            "votos": as_int(line[29:36]),
            "source_file": source_file,
        }
    )
    return row


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
    if any(pattern in text for pattern in ("PODEMOS", "IZQUIERDA UNIDA", "SUMAR", "CON ANDALUC", "POR ANDALUC")):
        return "SUMAR_PODEMOS_IU", "LEFT", False
    if re.search(r"(^|[^A-Z])IU([^A-Z]|$)", text):
        return "IU", "LEFT", False
    return "OTHER", "OTHER", False


def execute_sql_file(conn, relative_path: str) -> None:
    conn.execute(text((PROJECT_ROOT / relative_path).read_text()))


def ensure_model(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS marts"))
        execute_sql_file(conn, "sql/core/007_create_core_electoral_historical.sql")


def ensure_election(conn, election: ElectionZip) -> int:
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
                :tipo_eleccion_code,
                :tipo_eleccion_nombre,
                :anio,
                :mes,
                1,
                :election_date,
                :source_folder,
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
            "tipo_eleccion_code": election.tipo_eleccion_code,
            "tipo_eleccion_nombre": election.tipo_eleccion_nombre,
            "anio": election.anio,
            "mes": election.mes,
            "election_date": KNOWN_DATES.get((election.tipo_eleccion_code, election.anio, election.mes)),
            "source_folder": election.path.parent.name,
            "source_file": election.path.name,
        },
    ).one()
    return int(row.election_id)


def load_zip(engine, election: ElectionZip) -> dict[str, Any]:
    with zipfile.ZipFile(election.path) as archive:
        names = set(archive.namelist())
        candidates_file = f"03{election.stem_code}.DAT"
        totals_file = f"09{election.stem_code}.DAT"
        results_file = f"10{election.stem_code}.DAT"
        missing = [name for name in (candidates_file, totals_file, results_file) if name not in names]
        if missing:
            raise RuntimeError(f"{election.path.name}: missing required DAT files: {missing}")

        totals = [
            parse_mesa_totals(line, election.path.name)
            for line in read_zip_lines(archive, totals_file)
            if line[11:13] == TARGET_PROVINCE and line[13:16] == TARGET_MUNICIPALITY
        ]
        results = [
            parse_mesa_result(line, election.path.name)
            for line in read_zip_lines(archive, results_file)
            if line[11:13] == TARGET_PROVINCE and line[13:16] == TARGET_MUNICIPALITY
        ]
        used_candidates = {row["cod_candidatura"] for row in results}
        candidates = [
            parse_candidate(line)
            for line in read_zip_lines(archive, candidates_file)
            if line[8:14] in used_candidates
        ]

    if not totals or not results:
        raise RuntimeError(f"{election.path.name}: no Mijas mesa data found")

    candidates_df = pd.DataFrame(candidates).drop_duplicates(subset=["cod_candidatura"])
    totals_df = pd.DataFrame(totals).drop_duplicates(
        subset=["cod_provincia", "cod_municipio", "cod_distrito", "cod_seccion", "cod_mesa"]
    )
    results_df = pd.DataFrame(results).drop_duplicates(
        subset=["cod_provincia", "cod_municipio", "cod_distrito", "cod_seccion", "cod_mesa", "cod_candidatura"]
    )

    aliases = []
    for row in candidates_df.to_dict("records"):
        family, bloc, is_local = party_alias(row["siglas"], row["denominacion"])
        aliases.append(
            {
                "cod_candidatura": row["cod_candidatura"],
                "siglas_originales": row["siglas"],
                "denominacion_original": row["denominacion"],
                "normalized_party_family": family,
                "ideological_bloc": bloc,
                "is_local_party": is_local,
            }
        )
    alias_df = pd.DataFrame(aliases)

    with engine.begin() as conn:
        election_id = ensure_election(conn, election)
        for df in (candidates_df, totals_df, results_df, alias_df):
            df.insert(0, "election_id", election_id)

        candidates_df.to_sql("official_candidates_tmp", conn, schema="staging", if_exists="replace", index=False)
        totals_df.to_sql("official_totals_tmp", conn, schema="staging", if_exists="replace", index=False)
        results_df.to_sql("official_results_tmp", conn, schema="staging", if_exists="replace", index=False)
        alias_df.to_sql("official_alias_tmp", conn, schema="staging", if_exists="replace", index=False)

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
                    cod_cab_prov::char(6),
                    cod_cab_auto::char(6),
                    cod_cab_nac::char(6)
                FROM staging.official_candidates_tmp
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
                FROM staging.official_alias_tmp
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
                    cod_provincia::smallint,
                    cod_municipio::smallint,
                    cod_distrito::smallint,
                    cod_seccion::char(3),
                    cod_mesa::char(1)
                FROM staging.official_totals_tmp
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
                    censo_ine::integer,
                    censo_escrutinio::integer,
                    censo_cere::integer,
                    votantes_cere::integer,
                    votantes_avance1::integer,
                    votantes_avance2::integer,
                    votos_blanco::integer,
                    votos_nulos::integer,
                    votos_candidaturas::integer,
                    votos_ref_si::integer,
                    votos_ref_no::integer,
                    datos_oficiales::char(1),
                    censo::bigint,
                    votos_emitidos::bigint,
                    votos_validos::bigint,
                    source_file,
                    NOW()
                FROM staging.official_totals_tmp
                ON CONFLICT (election_id, cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa)
                DO UPDATE SET
                    seccion_id = EXCLUDED.seccion_id,
                    censo_ine = EXCLUDED.censo_ine,
                    censo_escrutinio = EXCLUDED.censo_escrutinio,
                    censo_cere = EXCLUDED.censo_cere,
                    votantes_cere = EXCLUDED.votantes_cere,
                    votantes_avance1 = EXCLUDED.votantes_avance1,
                    votantes_avance2 = EXCLUDED.votantes_avance2,
                    votos_blanco = EXCLUDED.votos_blanco,
                    votos_nulos = EXCLUDED.votos_nulos,
                    votos_candidaturas = EXCLUDED.votos_candidaturas,
                    votos_ref_si = EXCLUDED.votos_ref_si,
                    votos_ref_no = EXCLUDED.votos_ref_no,
                    datos_oficiales = EXCLUDED.datos_oficiales,
                    censo = EXCLUDED.censo,
                    votos_emitidos = EXCLUDED.votos_emitidos,
                    votos_validos = EXCLUDED.votos_validos,
                    source_file = EXCLUDED.source_file,
                    loaded_at = NOW();

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
                    NOW()
                FROM staging.official_results_tmp
                ON CONFLICT (
                    election_id,
                    cod_provincia,
                    cod_municipio,
                    cod_distrito,
                    cod_seccion,
                    cod_mesa,
                    cod_candidatura
                )
                DO UPDATE SET
                    seccion_id = EXCLUDED.seccion_id,
                    votos = EXCLUDED.votos,
                    source_file = EXCLUDED.source_file,
                    loaded_at = NOW();

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
                WITH votos AS (
                    SELECT
                        r.election_id,
                        r.seccion_id,
                        r.cod_candidatura,
                        SUM(r.votos)::bigint AS votos_partido,
                        MAX(r.source_file) AS source_file
                    FROM staging.official_results_tmp r
                    GROUP BY r.election_id, r.seccion_id, r.cod_candidatura
                ),
                totales AS (
                    SELECT
                        t.election_id,
                        t.seccion_id,
                        SUM(t.censo)::bigint AS censo,
                        SUM(t.votos_emitidos)::bigint AS votos_emitidos,
                        SUM(t.votos_validos)::bigint AS votos_validos,
                        SUM(t.votos_blanco)::bigint AS votos_blanco,
                        SUM(t.votos_nulos)::bigint AS votos_nulos
                    FROM staging.official_totals_tmp t
                    GROUP BY t.election_id, t.seccion_id
                )
                SELECT
                    v.election_id,
                    v.seccion_id,
                    :anio,
                    :mes,
                    :tipo_eleccion_code,
                    v.cod_candidatura,
                    c.siglas,
                    c.denominacion,
                    v.votos_partido,
                    t.votos_validos,
                    t.votos_emitidos,
                    t.votos_blanco,
                    t.votos_nulos,
                    t.censo,
                    ROUND(v.votos_partido::numeric / NULLIF(t.votos_validos, 0), 6),
                    'OFFICIAL_MESA_ZIP',
                    v.source_file
                FROM votos v
                JOIN totales t
                  ON t.election_id = v.election_id
                 AND t.seccion_id = v.seccion_id
                LEFT JOIN staging.official_candidates_tmp c
                  ON c.election_id = v.election_id
                 AND c.cod_candidatura = v.cod_candidatura
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

                DROP TABLE IF EXISTS staging.official_candidates_tmp;
                DROP TABLE IF EXISTS staging.official_totals_tmp;
                DROP TABLE IF EXISTS staging.official_results_tmp;
                DROP TABLE IF EXISTS staging.official_alias_tmp;
                """
            ),
            {
                "anio": election.anio,
                "mes": election.mes,
                "tipo_eleccion_code": election.tipo_eleccion_code,
            },
        )

    return {
        "file": election.path.name,
        "election_id": election_id,
        "tipo_eleccion_code": election.tipo_eleccion_code,
        "anio": election.anio,
        "mes": election.mes,
        "mesas": len(totals_df),
        "resultados_mesa": len(results_df),
        "candidaturas": len(candidates_df),
        "secciones": totals_df["seccion_id"].nunique(),
    }


def main() -> None:
    args = parse_args()
    engine = create_engine(args.db)
    ensure_model(engine)

    zips: list[ElectionZip] = []
    for folder in args.folders:
        for path in sorted((args.root / folder).glob("*.zip")):
            election = parse_zip_name(path)
            if election:
                zips.append(election)

    if not zips:
        raise SystemExit("No official MESA ZIP files found.")

    summaries = [load_zip(engine, election) for election in zips]
    for summary in summaries:
        print(
            "LOADED "
            f"file={summary['file']} election_id={summary['election_id']} "
            f"type={summary['tipo_eleccion_code']} year={summary['anio']} month={summary['mes']} "
            f"sections={summary['secciones']} tables={summary['mesas']} "
            f"candidates={summary['candidaturas']} rows={summary['resultados_mesa']}"
        )


if __name__ == "__main__":
    main()
