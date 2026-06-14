from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.auth import ensure_authenticated
from components.branding import (
    SOCTRACE_CONTINUOUS_SCALE,
    apply_plotly_branding,
    configure_page,
    render_section_header,
)
from components.export import render_export_buttons
from components.filters import sidebar_filters
from components.formatters import density_level, format_density
from components.metrics import render_overview_metrics
from components.table_ui import dataframe_auto_height, present_table
from services.queries import get_filter_options, get_panel_data, get_sections_geojson

configure_page("Mapa")
ensure_authenticated()

render_section_header(
    "Mapa por Sección",
    "Explora la huella territorial del dato con una lectura limpia, ejecutiva y lista para demo.",
    eyebrow="Vista territorial",
)

options = get_filter_options()
year, sigla = sidebar_filters(options)
df = get_panel_data(year=year, sigla=sigla)

metric_options = [
    ("Participación", "participacion"),
    ("Densidad", "densidad"),
    ("Población", "pob_total"),
    ("PP % voto", "pct_pp"),
    ("PSOE % voto", "pct_psoe"),
    ("VOX % voto", "pct_vox"),
]
metric_labels = [label for label, _ in metric_options]
metric_map = dict(metric_options)
metric_label = st.selectbox("Variable del mapa", metric_labels)
metric_col = metric_map[metric_label]
show_density_context = metric_col in {"densidad", "pob_total"}

area_values = sorted([a for a in df["zona_macro"].dropna().unique().tolist() if str(a).strip()])
area_choices = ["Todas"] + area_values
selected_area = st.sidebar.selectbox("Área", area_choices)
sort_choice = st.sidebar.radio("Orden", ["Mayor a menor", "Menor a mayor"], horizontal=False)
sort_ascending = sort_choice == "Menor a mayor"

if selected_area != "Todas":
    df = df[df["zona_macro"] == selected_area].copy()

render_overview_metrics(df)

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

debug_mode = st.sidebar.checkbox("Modo debug tecnico", value=False, key="debug_mode_mapa")

# Evita columnas duplicadas en el agregado cuando la metrica seleccionada es "densidad".
agg_value_cols = [metric_col] if metric_col == "densidad" else [metric_col, "densidad"]

map_df = (
    df.groupby(
        ["seccion_id", "seccion_numero_visible", "nombre_barrio", "zona_macro", "label_cliente"],
        as_index=False,
    )[agg_value_cols]
    .mean(numeric_only=True)
    .rename(columns={metric_col: "metric_value"})
)

if metric_col == "densidad":
    map_df["densidad_value"] = map_df["metric_value"]
else:
    map_df = map_df.rename(columns={"densidad": "densidad_value"})

# Debug temporal para inspeccionar estructura de columnas.
dup_cols = map_df.columns[map_df.columns.duplicated()].tolist()
if debug_mode:
    with st.sidebar.expander("Debug columnas map_df", expanded=False):
        st.write("map_df.columns:", map_df.columns.tolist())
        st.write("duplicadas:", dup_cols)

# Protección explícita para evitar errores de reindex si reaparecen duplicados.
if dup_cols:
    map_df = map_df.loc[:, ~map_df.columns.duplicated()].copy()

map_df["seccion_visible"] = map_df["seccion_numero_visible"].apply(
    lambda x: f"Sección {str(x).zfill(2)}" if str(x).strip() else "Sección 00"
)
if show_density_context:
    map_df["Densidad"] = map_df["densidad_value"].apply(format_density)
    map_df["Nivel"] = map_df["densidad_value"].apply(density_level)

hover_data = {
    "seccion_visible": False,
    "nombre_barrio": True,
    "zona_macro": True,
    "metric_value": ":.4f",
    "densidad_value": False,
    "label_cliente": False,
}
if show_density_context:
    hover_data["Densidad"] = True
    hover_data["Nivel"] = True
if debug_mode:
    hover_data["seccion_id"] = True

# Robustez: Plotly falla si hover_data incluye columnas que no existen en map_df.
hover_data = {k: v for k, v in hover_data.items() if k in map_df.columns}

if debug_mode:
    with st.sidebar.expander("Debug hover_data", expanded=False):
        st.write("hover_data final:", hover_data)

geojson = get_sections_geojson()
fig = px.choropleth_mapbox(
    map_df,
    geojson=geojson,
    locations="seccion_id",
    featureidkey="properties.seccion_id",
    color="metric_value",
    hover_name="seccion_visible",
    hover_data=hover_data,
    color_continuous_scale=SOCTRACE_CONTINUOUS_SCALE,
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 36.595, "lon": -4.637},
    opacity=0.7,
)
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=620)
fig.update_traces(marker_line_width=1.1, marker_line_color="rgba(255,255,255,0.7)")
fig.update_coloraxes(colorbar_title=metric_label)
fig = go.Figure(fig)
apply_plotly_branding(fig)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Listado de secciones")
sections_df = map_df.sort_values("metric_value", ascending=sort_ascending).copy()

table_cols = ["seccion_numero_visible", "nombre_barrio", "zona_macro", "metric_value"]
if show_density_context:
    table_cols.extend(["densidad_value", "Nivel"])

table_view = sections_df[table_cols].rename(columns={"metric_value": metric_col})
table_view["seccion_numero_visible"] = table_view["seccion_numero_visible"].apply(
    lambda x: f"Sección {str(x).zfill(2)}" if str(x).strip() else "Sección 00"
)
table_view = table_view.rename(columns={"seccion_numero_visible": "seccion"})
if show_density_context and metric_col != "densidad":
    table_view["densidad"] = table_view["densidad_value"]
if "densidad_value" in table_view.columns:
    table_view = table_view.drop(columns=["densidad_value"])
table_view = table_view.rename(columns={metric_col: metric_label})

# UX: en Poblacion, mostrar Densidad y luego Nivel.
if metric_col == "pob_total":
    ordered_cols = ["seccion", "nombre_barrio", "zona_macro", "Población", "densidad", "Nivel"]
    if debug_mode:
        ordered_cols.append("seccion_id")
    existing_cols = [c for c in ordered_cols if c in table_view.columns]
    remaining_cols = [c for c in table_view.columns if c not in existing_cols]
    table_view = table_view[existing_cols + remaining_cols]

if debug_mode:
    table_view["seccion_id"] = sections_df["seccion_id"].values
dataframe_auto_height(present_table(table_view), use_container_width=True, hide_index=True)
render_export_buttons(sections_df, base_name="soctrace_mapa_listado", title="soctrace Mapa Listado Secciones")
