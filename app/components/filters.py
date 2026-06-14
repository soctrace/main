from __future__ import annotations

import streamlit as st


def sidebar_filters(options: dict) -> tuple[int | None, str | None]:
    st.sidebar.markdown("### Filtros")
    st.sidebar.caption("Ajusta el marco territorial y electoral de la vista.")

    year_choices = [None] + options.get("years", [])
    sigla_choices = [None] + options.get("siglas", [])

    year = st.sidebar.selectbox(
        "Ano",
        options=year_choices,
        format_func=lambda x: "Todos" if x is None else str(x),
    )
    sigla = st.sidebar.selectbox(
        "Partido ganador",
        options=sigla_choices,
        format_func=lambda x: "Todos" if x is None else str(x),
    )

    return year, sigla
