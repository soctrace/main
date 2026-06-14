from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st


def _sanitize_df_for_export(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for col in cleaned.columns:
        cleaned[col] = cleaned[col].astype(str).str.replace("\n", " ", regex=False)
    return cleaned


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return _sanitize_df_for_export(df).to_csv(index=False).encode("utf-8")


def to_pdf_bytes(df: pd.DataFrame, title: str = "SocTrace Export") -> bytes:
    from fpdf import FPDF

    export_df = _sanitize_df_for_export(df).head(300)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, txt=title, ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, txt=f"Generated at: {datetime.utcnow().isoformat()} UTC", ln=True)
    pdf.ln(2)

    if export_df.empty:
        pdf.cell(0, 8, txt="No data available.", ln=True)
    else:
        cols = list(export_df.columns)
        col_count = max(len(cols), 1)
        usable_width = 277  # A4 landscape width (297) minus margins.
        col_width = max(18, usable_width / col_count)

        pdf.set_font("Helvetica", style="B", size=8)
        for col in cols:
            pdf.cell(col_width, 7, txt=str(col)[:20], border=1)
        pdf.ln()

        pdf.set_font("Helvetica", size=7)
        for _, row in export_df.iterrows():
            for value in row.tolist():
                pdf.cell(col_width, 6, txt=str(value)[:24], border=1)
            pdf.ln()

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", errors="replace")
    if isinstance(raw, bytearray):
        return bytes(raw)
    if isinstance(raw, BytesIO):
        return raw.getvalue()
    return raw


def render_export_buttons(
    df: pd.DataFrame,
    base_name: str,
    title: str = "SocTrace Export",
) -> None:
    if df.empty:
        return

    c1, c2 = st.columns(2)
    c1.download_button(
        label="Descargar CSV",
        data=to_csv_bytes(df),
        file_name=f"{base_name}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    try:
        pdf_bytes = to_pdf_bytes(df, title=title)
    except ModuleNotFoundError:
        c2.info("Instala `fpdf2` para habilitar PDF.")
        return

    c2.download_button(
        label="Descargar PDF",
        data=pdf_bytes,
        file_name=f"{base_name}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
