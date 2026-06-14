from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.auth import ensure_authenticated
from components.branding import SOCTRACE_SEQUENCE, apply_plotly_branding, configure_page, render_section_header
from components.export import render_export_buttons
from components.formatters import density_level, format_number_es
from components.table_ui import dataframe_auto_height, present_table
from services.queries import get_filter_options, get_panel_data

configure_page("Comparador")
ensure_authenticated()

render_section_header(
    "Comparador de Secciones",
    "Benchmark territorial con una presentación más clara para detectar diferencias críticas entre áreas.",
    eyebrow="Comparativa",
)

options = get_filter_options()
year = st.selectbox("Ano", options.get("years", []))
pool_sections = options.get("sections", [])
section_labels = options.get("section_labels", {})

selected_sections = st.multiselect(
    "Selecciona entre 2 y 5 secciones",
    pool_sections,
    default=pool_sections[:2],
    max_selections=5,
    format_func=lambda sid: section_labels.get(sid, sid),
)
debug_mode = st.sidebar.checkbox("Modo debug tecnico", value=False, key="debug_mode_comparador")

if len(selected_sections) < 2:
    st.info("Selecciona al menos 2 secciones para comparar.")
    st.stop()

df = get_panel_data(year=year)
df = df[df["seccion_id"].isin(selected_sections)].copy()

if df.empty:
    st.warning("No hay datos para ese filtro.")
    st.stop()

agg = (
    df.groupby(
        ["seccion_id", "seccion_numero_visible", "nombre_barrio", "zona_macro", "label_cliente"],
        as_index=False,
    )[
        ["pob_total", "densidad", "participacion", "pct_pp", "pct_psoe", "pct_vox"]
    ]
    .mean(numeric_only=True)
)
agg["seccion_visible"] = agg["seccion_numero_visible"].apply(
    lambda x: f"Sección {str(x).zfill(2)}" if str(x).strip() else "Sección 00"
)
agg["Nivel"] = agg["densidad"].apply(density_level)
agg["Densidad (hab/km²)"] = agg["densidad"].apply(lambda v: format_number_es(v, decimals=1))

table_cols = [
    "seccion_visible",
    "nombre_barrio",
    "zona_macro",
    "pob_total",
    "densidad",
    "Nivel",
    "participacion",
    "pct_pp",
    "pct_psoe",
    "pct_vox",
]
if debug_mode:
    table_cols = ["seccion_id"] + table_cols
table_df = agg[table_cols].copy()
dataframe_auto_height(present_table(table_df), use_container_width=True, hide_index=True)
render_export_buttons(agg, base_name="soctrace_comparador", title="SocTrace Comparador")

metric = st.selectbox(
    "Metrica a visualizar",
    ["pob_total", "densidad", "participacion", "pct_pp", "pct_psoe", "pct_vox"],
)
fig = px.bar(
    agg,
    x="seccion_visible",
    y=metric,
    color="seccion_visible",
    color_discrete_sequence=SOCTRACE_SEQUENCE,
    hover_data={
        "seccion_visible": False,
        "nombre_barrio": True,
        "zona_macro": True,
        "densidad": False,
        "Densidad (hab/km²)": True,
        "Nivel": True,
        "label_cliente": False,
        "seccion_id": debug_mode,
    },
)
if metric in {"participacion", "pct_pp", "pct_psoe", "pct_vox"}:
    fig.update_layout(yaxis_tickformat=".0%")
fig.update_layout(height=420, showlegend=False)
apply_plotly_branding(fig)
st.plotly_chart(fig, use_container_width=True)
