from __future__ import annotations

import math

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.auth import ensure_authenticated
from components.branding import (
    SOCTRACE_CONTINUOUS_SCALE,
    apply_plotly_branding,
    configure_page,
)
from services.queries import get_filter_options, get_panel_data, get_sections_geojson


METRIC_OPTIONS = [
    ("Participación", "participacion"),
    ("Densidad", "densidad"),
    ("Población", "pob_total"),
    ("PP % voto", "pct_pp"),
    ("PSOE % voto", "pct_psoe"),
    ("VOX % voto", "pct_vox"),
]
METRIC_HELP = {
    "Participación": "Mide activación electoral en el territorio.",
    "Densidad": "Aporta contexto urbano inmediato.",
    "Población": "Dimensiona masa crítica por sección.",
    "PP % voto": "Lectura de fortaleza relativa del PP.",
    "PSOE % voto": "Lectura de fortaleza relativa del PSOE.",
    "VOX % voto": "Lectura de fortaleza relativa de VOX.",
}
METRIC_MAP = dict(METRIC_OPTIONS)


def _format_pct(value: float | int | None) -> str:
    numeric = float(value or 0)
    if math.isnan(numeric):
        numeric = 0.0
    return f"{numeric * 100:.1f}%"


def _format_density(value: float | int | None) -> str:
    numeric = float(value or 0)
    if math.isnan(numeric):
        numeric = 0.0
    return f"{numeric:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " hab/km²"


def _format_int(value: float | int | None) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _build_map_df(df):
    agg = (
        df.groupby(
            ["seccion_id", "seccion_numero_visible", "nombre_barrio", "zona_macro", "label_cliente"],
            as_index=False,
        )[
            ["participacion", "densidad", "pob_total", "pct_pp", "pct_psoe", "pct_vox"]
        ]
        .mean(numeric_only=True)
    )
    agg["seccion_visible"] = agg["seccion_numero_visible"].apply(
        lambda x: f"Sección {str(x).zfill(2)}" if str(x).strip() else "Sección 00"
    )
    agg["participacion_label"] = agg["participacion"].apply(_format_pct)
    agg["densidad_label"] = agg["densidad"].apply(_format_density)
    agg["pob_total_label"] = agg["pob_total"].apply(_format_int)
    agg["pct_pp_label"] = agg["pct_pp"].apply(_format_pct)
    agg["pct_psoe_label"] = agg["pct_psoe"].apply(_format_pct)
    agg["pct_vox_label"] = agg["pct_vox"].apply(_format_pct)
    return agg


configure_page("Home", hide_sidebar=True, render_sidebar=False)
ensure_authenticated()

options = get_filter_options()
default_year = options.get("years", [None])[0]
default_sigla = "Todas"

if "home_selected_metric" not in st.session_state:
    st.session_state.home_selected_metric = "Participación"

sigla_filter = None if default_sigla == "Todas" else default_sigla
df = get_panel_data(year=default_year, sigla=sigla_filter)

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

map_df = _build_map_df(df)
if map_df.empty:
    st.warning("No hay datos suficientes para representar el mapa con los filtros activos.")
    st.stop()

selected_metric_label = st.session_state.home_selected_metric
metric_col = METRIC_MAP[selected_metric_label]

st.markdown(
    """
    <div class="soc-map-shell soc-map-shell--immersive">
        <div class="soc-map-toolbar">
            <div class="soc-map-toolbar-note">Mapa principal</div>
        </div>
    """,
    unsafe_allow_html=True,
)

_, toolbar_layers, toolbar_logout = st.columns([0.78, 0.14, 0.08], vertical_alignment="center")
with toolbar_layers:
    with st.popover("Capas", use_container_width=True):
        st.markdown(
            '<p class="soc-popover-body">Panel flotante contextual del mapa. Se mantiene una sola capa activa para preservar la lógica actual sin reescribir el comportamiento analítico.</p>',
            unsafe_allow_html=True,
        )
        selected_layer = st.radio(
            "Capas analíticas",
            [label for label, _ in METRIC_OPTIONS],
            index=[label for label, _ in METRIC_OPTIONS].index(st.session_state.home_selected_metric),
            label_visibility="collapsed",
        )
        if selected_layer != st.session_state.home_selected_metric:
            st.session_state.home_selected_metric = selected_layer
            st.rerun()
        st.caption(METRIC_HELP[st.session_state.home_selected_metric])

with toolbar_logout:
    if st.button("Salir", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.auth_user = None
        st.rerun()

geojson = get_sections_geojson()
fig = px.choropleth_mapbox(
    map_df,
    geojson=geojson,
    locations="seccion_id",
    featureidkey="properties.seccion_id",
    color=metric_col,
    custom_data=["seccion_id"],
    hover_name="seccion_visible",
    hover_data={
        "seccion_visible": False,
        "nombre_barrio": True,
        "zona_macro": True,
        "participacion_label": True,
        "densidad_label": True,
        "pob_total_label": True,
        "pct_pp_label": True,
        "pct_psoe_label": True,
        "pct_vox_label": True,
        "seccion_id": False,
        metric_col: False,
    },
    color_continuous_scale=SOCTRACE_CONTINUOUS_SCALE,
    mapbox_style="carto-darkmatter",
    zoom=10,
    center={"lat": 36.595, "lon": -4.637},
    opacity=0.9,
)
fig.update_traces(marker_line_width=1.2, marker_line_color="rgba(255,255,255,0.14)")
fig.update_layout(height=900, margin={"r": 0, "t": 0, "l": 0, "b": 0})
fig.update_coloraxes(colorbar_title=selected_metric_label)
fig = go.Figure(fig)
apply_plotly_branding(fig)

st.plotly_chart(fig, use_container_width=True, key="home_intelligence_map")
st.markdown("</div>", unsafe_allow_html=True)
