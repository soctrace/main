from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from services.config import get_database_url


@st.cache_resource
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


def fetch_df(query: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
