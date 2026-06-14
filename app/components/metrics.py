from __future__ import annotations

import pandas as pd

from components.branding import render_metric_cards


def render_overview_metrics(df: pd.DataFrame) -> None:
    if df.empty:
        return

    render_metric_cards(
        [
            {
                "label": "Secciones",
                "value": f"{int(df['seccion_id'].nunique())}",
                "help": "Cobertura territorial disponible para el análisis actual.",
            },
            {
                "label": "Población total",
                "value": f"{int(df['pob_total'].fillna(0).sum()):,}".replace(",", "."),
                "help": "Suma agregada de población en la selección activa.",
            },
            {
                "label": "Participación media",
                "value": f"{(df['participacion'].dropna().mean() * 100):.1f}%",
                "help": "Promedio agregado del bloque filtrado.",
            },
            {
                "label": "Filas analíticas",
                "value": f"{int(len(df))}",
                "help": "Registros listos para visualización y exportación.",
            },
        ]
    )
