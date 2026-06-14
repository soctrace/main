from __future__ import annotations

import plotly.express as px
import streamlit as st

from components.auth import ensure_authenticated
from components.branding import (
    SOCTRACE_SEQUENCE,
    apply_plotly_branding,
    configure_page,
    render_metric_cards,
    render_section_header,
)
from components.export import render_export_buttons
from components.formatters import density_level, format_density
from components.table_ui import dataframe_auto_height, present_table
from services.queries import get_filter_options, get_section_profile

configure_page("Perfil")
ensure_authenticated()

render_section_header(
    "Perfil de Sección",
    "Ficha premium para interpretar rápidamente contexto demográfico, densidad y comportamiento electoral.",
    eyebrow="Vista analítica",
)

options = get_filter_options()
sections = options.get("sections", [])
section_labels = options.get("section_labels", {})

if not sections:
    st.warning("No hay secciones disponibles.")
    st.stop()

selected_section = st.selectbox(
    "Seccion",
    sections,
    format_func=lambda sid: section_labels.get(sid, sid),
)
debug_mode = st.sidebar.checkbox("Modo debug tecnico", value=False, key="debug_mode_perfil")
profile = get_section_profile(selected_section)

if profile.empty:
    st.warning("No hay datos para la seccion seleccionada.")
    st.stop()

latest = profile.sort_values(["anio", "election_id"]).iloc[-1]
seccion_visible = f"Sección {str(latest.get('seccion_numero_visible', '00')).zfill(2)}"
nombre_barrio = str(latest.get("nombre_barrio", "") or "")
zona_macro = str(latest.get("zona_macro", "") or "")
label_cliente = str(latest.get("label_cliente", seccion_visible))

st.subheader(seccion_visible)
if nombre_barrio:
    st.write(nombre_barrio)
if zona_macro:
    st.caption(zona_macro)
if debug_mode:
    st.caption(f"Referencia interna: {selected_section}")
    st.caption(label_cliente)

render_metric_cards(
    [
        {
            "label": "Población",
            "value": f"{int(latest.get('pob_total', 0) or 0):,}".replace(",", "."),
            "help": "Volumen estimado de residentes en la sección.",
        },
        {
            "label": "Densidad",
            "value": format_density(latest.get("densidad")),
            "help": "Habitantes por km² para lectura de presión urbana.",
        },
        {
            "label": "Participación",
            "value": f"{float(latest.get('participacion', 0) or 0) * 100:.1f}%",
            "help": "Comportamiento electoral agregado más reciente.",
        },
        {
            "label": "Ganador",
            "value": str(latest.get("sigla_ganadora", "-")),
            "help": "Partido con mayor peso en la última observación.",
        },
    ]
)
dens_level = density_level(latest.get("densidad"))
if dens_level:
    st.caption(f"Nivel de densidad: {dens_level}")

chart_df = profile[["anio", "participacion", "pct_pp", "pct_psoe", "pct_vox"]].copy()
melted = chart_df.melt(id_vars=["anio"], var_name="indicador", value_name="valor")
fig = px.line(
    melted,
    x="anio",
    y="valor",
    color="indicador",
    markers=True,
    color_discrete_sequence=SOCTRACE_SEQUENCE,
)
fig.update_layout(height=360, yaxis_tickformat=".0%")
apply_plotly_branding(fig)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Detalle completo")
cols = [
    "seccion_numero_visible",
    "nombre_barrio",
    "zona_macro",
    "anio",
    "election_id",
    "pob_total",
    "densidad",
    "participacion",
    "pct_pp",
    "pct_psoe",
    "pct_vox",
]
if debug_mode:
    cols = ["seccion_id"] + cols
detail_df = profile[[c for c in cols if c in profile.columns]].copy()
detail_df = detail_df.rename(columns={"seccion_numero_visible": "seccion"})
if "densidad" in detail_df.columns:
    detail_df["Nivel"] = detail_df["densidad"].apply(density_level)
dataframe_auto_height(present_table(detail_df), use_container_width=True, hide_index=True)
render_export_buttons(
    profile,
    base_name=f"soctrace_perfil_{selected_section}",
    title=f"soctrace Perfil {selected_section}",
)
