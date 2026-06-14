from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.auth import ensure_authenticated
from components.branding import SOCTRACE_SEQUENCE, apply_plotly_branding, configure_page, render_section_header
from components.export import render_export_buttons
from components.formatters import density_level
from components.table_ui import dataframe_auto_height, present_table
from services.queries import get_filter_options, get_section_profile

configure_page("Tendencias")
ensure_authenticated()

render_section_header(
    "Tendencias Temporales",
    "Evolución histórica de cada sección con una lectura más limpia y orientada a presentación comercial.",
    eyebrow="Serie temporal",
)

options = get_filter_options()
sections = options.get("sections", [])
section_labels = options.get("section_labels", {})

section = st.selectbox(
    "Seccion",
    sections,
    format_func=lambda sid: section_labels.get(sid, sid),
)
debug_mode = st.sidebar.checkbox("Modo debug tecnico", value=False, key="debug_mode_tendencias")
profile = get_section_profile(section)

if profile.empty:
    st.warning("No hay datos para la seccion seleccionada.")
    st.stop()

top = profile.iloc[0]
seccion_visible = f"Sección {str(top.get('seccion_numero_visible', '00')).zfill(2)}"
nombre_barrio = str(top.get("nombre_barrio", "") or "")
zona_macro = str(top.get("zona_macro", "") or "")

st.subheader(seccion_visible)
if nombre_barrio:
    st.write(nombre_barrio)
if zona_macro:
    st.caption(zona_macro)
if debug_mode:
    st.caption(f"Referencia interna: {section}")

metrics = st.multiselect(
    "Metricas",
    ["pob_total", "densidad", "participacion", "pct_pp", "pct_psoe", "pct_vox"],
    default=["pob_total", "participacion"],
)

if not metrics:
    st.info("Selecciona al menos una metrica.")
    st.stop()

ts = profile[["anio"] + metrics].copy()
ts = ts.groupby("anio", as_index=False).mean(numeric_only=True)
melted = ts.melt(id_vars="anio", var_name="metrica", value_name="valor")

fig = px.line(
    melted,
    x="anio",
    y="valor",
    color="metrica",
    markers=True,
    color_discrete_sequence=SOCTRACE_SEQUENCE,
)
fig.update_layout(height=460)
apply_plotly_branding(fig)
st.plotly_chart(fig, use_container_width=True)

table_df = ts.copy()
table_df.insert(0, "seccion", f"Sección {str(top.get('seccion_numero_visible', '00')).zfill(2)}")
table_df.insert(1, "nombre_barrio", nombre_barrio)
table_df.insert(2, "zona_macro", zona_macro)
if "densidad" in table_df.columns:
    table_df["Nivel"] = table_df["densidad"].apply(density_level)
if debug_mode:
    table_df.insert(0, "seccion_id", section)
dataframe_auto_height(present_table(table_df), use_container_width=True, hide_index=True)
render_export_buttons(ts, base_name=f"soctrace_tendencias_{section}", title=f"soctrace Tendencias {section}")
