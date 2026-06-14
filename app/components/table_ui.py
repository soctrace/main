from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from components.formatters import format_number_es


UI_COLUMN_RENAMES = {
    "seccion": "Sección",
    "seccion_visible": "Sección",
    "seccion_numero_visible": "Sección",
    "nombre_barrio": "Nombre",
    "zona_macro": "Área",
    "Participacion": "Participación %",
    "participacion": "Participación %",
    "Participación": "Participación %",
    "pob_total": "Población",
    "Poblacion": "Población",
    "densidad": "Densidad (hab/km²)",
    "Densidad": "Densidad (hab/km²)",
    "pct_pp": "PP % voto",
    "pct_psoe": "PSOE % voto",
    "pct_vox": "VOX % voto",
}


def _section_value_to_short(value) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    match = re.search(r"(\d{1,3})$", text)
    if match:
        return str(int(match.group(1))).zfill(2)

    return text


def present_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    section_col = None
    for candidate in ("seccion", "seccion_visible", "seccion_numero_visible"):
        if candidate in out.columns:
            section_col = candidate
            break

    if section_col:
        out[section_col] = out[section_col].apply(_section_value_to_short)

    # Capa de presentacion: densidad visible en hab/km² y formato ES con 1 decimal.
    for density_col in ("densidad", "Densidad"):
        if density_col in out.columns and pd.api.types.is_numeric_dtype(out[density_col]):
            out[density_col] = out[density_col].apply(lambda v: format_number_es(v, decimals=1))

    # Capa de presentacion: poblacion con separador de miles y sin decimales.
    for population_col in ("pob_total", "Poblacion", "Población"):
        if population_col in out.columns and pd.api.types.is_numeric_dtype(out[population_col]):
            out[population_col] = out[population_col].apply(lambda v: format_number_es(v, decimals=0))

    # Capa de presentacion: ratios porcentuales (participacion y voto partidos) a % con 1 decimal.
    pct_cols = (
        "participacion",
        "Participacion",
        "Participación",
        "Participación %",
        "pct_pp",
        "pct_psoe",
        "pct_vox",
        "PP % voto",
        "PSOE % voto",
        "VOX % voto",
    )
    for pct_col in pct_cols:
        if pct_col in out.columns and pd.api.types.is_numeric_dtype(out[pct_col]):
            series = out[pct_col].dropna()
            if not series.empty and series.abs().le(1.5).all():
                display_series = out[pct_col] * 100
            else:
                display_series = out[pct_col]
            out[pct_col] = display_series.apply(lambda v: format_number_es(v, decimals=1))

    out = out.rename(columns=UI_COLUMN_RENAMES)
    out = out.loc[:, ~out.columns.duplicated()].copy()
    return out


def dataframe_auto_height(
    df: pd.DataFrame,
    *,
    use_container_width: bool = True,
    hide_index: bool = True,
    row_px: int = 35,
    header_px: int = 42,
    padding_px: int = 8,
) -> None:
    """
    Renderiza un dataframe sin scroll interno calculando una altura suficiente
    para mostrar todas las filas.
    """
    n_rows = len(df.index)
    height = max(180, header_px + (n_rows * row_px) + padding_px)
    st.dataframe(
        df,
        use_container_width=use_container_width,
        hide_index=hide_index,
        height=height,
    )
