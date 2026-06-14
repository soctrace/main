from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from services.db import fetch_df


SECTION_NUM_SQL = """
COALESCE(
    NULLIF(d.seccion_numero_visible, ''),
    LPAD((RIGHT(mfp.seccion_id, 3)::int)::text, 2, '0')
)
"""

SECTION_LABEL_SQL = f"""
COALESCE(
    NULLIF(d.label_cliente, ''),
    CASE
        WHEN NULLIF(d.nombre_barrio, '') IS NOT NULL
        THEN 'Sección ' || {SECTION_NUM_SQL} || ' · ' || d.nombre_barrio
        ELSE 'Sección ' || {SECTION_NUM_SQL}
    END
)
"""


@st.cache_data(ttl=300)
def get_overview() -> dict:
    df = fetch_df(
        """
        SELECT
            COUNT(*) AS n_rows,
            COUNT(DISTINCT seccion_id) AS n_secciones,
            COUNT(DISTINCT election_id) AS n_elections,
            MIN(anio) AS min_anio,
            MAX(anio) AS max_anio
        FROM marts.mijas_features_panel
        """
    )
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


@st.cache_data(ttl=300)
def get_filter_options() -> dict:
    years = fetch_df(
        """
        SELECT DISTINCT anio
        FROM marts.mijas_features_panel
        WHERE anio IS NOT NULL
        ORDER BY anio DESC
        """
    )["anio"].tolist()

    siglas = fetch_df(
        """
        SELECT DISTINCT sigla_ganadora
        FROM marts.mijas_features_panel
        WHERE sigla_ganadora IS NOT NULL
        ORDER BY sigla_ganadora
        """
    )["sigla_ganadora"].tolist()

    section_df = fetch_df(
        f"""
        SELECT DISTINCT
            mfp.seccion_id,
            {SECTION_LABEL_SQL} AS label_cliente
        FROM marts.mijas_features_panel mfp
        LEFT JOIN marts.dim_seccion_display d
          ON d.seccion_id = mfp.seccion_id
        WHERE mfp.seccion_id IS NOT NULL
        ORDER BY mfp.seccion_id
        """
    )

    sections = section_df["seccion_id"].tolist()
    section_labels = dict(zip(section_df["seccion_id"], section_df["label_cliente"]))

    return {
        "years": years,
        "siglas": siglas,
        "sections": sections,
        "section_labels": section_labels,
    }


@st.cache_data(ttl=300)
def get_panel_data(year: int | None = None, sigla: str | None = None) -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT
            mfp.seccion_id,
            mfp.anio,
            mfp.election_id,
            mfp.area_km2,
            mfp.densidad,
            mfp.pob_total,
            mfp.participacion,
            mfp.votos_emitidos,
            mfp.sigla_ganadora,
            mfp.votos_ganador,
            mfp.pct_pp,
            mfp.pct_psoe,
            mfp.pct_vox,
            {SECTION_NUM_SQL} AS seccion_numero_visible,
            COALESCE(NULLIF(d.nombre_barrio, ''), '') AS nombre_barrio,
            COALESCE(NULLIF(d.zona_macro, ''), '') AS zona_macro,
            {SECTION_LABEL_SQL} AS label_cliente
        FROM marts.mijas_features_panel mfp
        LEFT JOIN marts.dim_seccion_display d
          ON d.seccion_id = mfp.seccion_id
        WHERE 1=1
          AND (:year IS NULL OR mfp.anio = :year)
          AND (:sigla IS NULL OR mfp.sigla_ganadora = :sigla)
        ORDER BY mfp.anio DESC, mfp.seccion_id
        """,
        params={"year": year, "sigla": sigla},
    )


@st.cache_data(ttl=300)
def get_section_profile(seccion_id: str) -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT
            mfp.*,
            {SECTION_NUM_SQL} AS seccion_numero_visible,
            COALESCE(NULLIF(d.nombre_barrio, ''), '') AS nombre_barrio,
            COALESCE(NULLIF(d.zona_macro, ''), '') AS zona_macro,
            {SECTION_LABEL_SQL} AS label_cliente
        FROM marts.mijas_features_panel mfp
        LEFT JOIN marts.dim_seccion_display d
          ON d.seccion_id = mfp.seccion_id
        WHERE mfp.seccion_id = :seccion_id
        ORDER BY mfp.anio, mfp.election_id
        """,
        params={"seccion_id": seccion_id},
    )


@st.cache_data(ttl=300)
def get_sections_geojson() -> dict:
    df = fetch_df(
        """
        SELECT
            seccion_id,
            seccion_numero_visible,
            COALESCE(nombre_barrio, '') AS nombre_barrio,
            COALESCE(zona_macro, '') AS zona_macro,
            label_cliente,
            geom_json
        FROM marts.v_mapa_seccion_2023
        """
    )

    features = []
    for _, row in df.iterrows():
        features.append(
            {
                "type": "Feature",
                "id": row["seccion_id"],
                "properties": {
                    "seccion_id": row["seccion_id"],
                    "seccion_numero_visible": row["seccion_numero_visible"],
                    "nombre_barrio": row["nombre_barrio"],
                    "zona_macro": row["zona_macro"],
                    "label_cliente": row["label_cliente"],
                },
                "geometry": json.loads(row["geom_json"]),
            }
        )

    return {"type": "FeatureCollection", "features": features}
