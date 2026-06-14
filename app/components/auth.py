from __future__ import annotations

import base64
import os
from pathlib import Path

import streamlit as st

from services.config import get_project_name


def _get_valid_credentials() -> tuple[str, str]:
    env_user = os.getenv("SOCTRACE_APP_USERNAME")
    env_pass = os.getenv("SOCTRACE_APP_PASSWORD")

    username = env_user or "admin"
    password = env_pass or "soctrace-demo"
    return str(username), str(password)


def _get_logo_data_uri() -> str | None:
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "icon.png"
    if not logo_path.exists():
        return None
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def ensure_authenticated() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    valid_user, valid_pass = _get_valid_credentials()
    logo_data_uri = _get_logo_data_uri()

    if st.session_state.authenticated:
        return

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }

        [data-testid="collapsedControl"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1.45, 0.8, 1.45])
    with center:
        logo_markup = (
            f'<img src="{logo_data_uri}" alt="soctrace" class="soc-auth-logo-image" />'
            if logo_data_uri
            else '<div class="soc-auth-logo-fallback">ST</div>'
        )
        st.markdown('<section class="soc-auth-stage"><div class="soc-auth-stack">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="soc-auth-shell">
                <div class="soc-auth-logo">
                    {logo_markup}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="soc-auth-form">', unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            user = st.text_input(
                "Usuario",
                placeholder="Usuario",
                label_visibility="collapsed",
            )
            pwd = st.text_input(
                "Contrasena",
                type="password",
                placeholder="Contraseña",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=False)

            if submitted:
                if user == valid_user and pwd == valid_pass:
                    st.session_state.authenticated = True
                    st.session_state.auth_user = user
                    st.rerun()
                st.error("Credenciales no validas.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f'<p class="soc-auth-footer">{get_project_name().upper()} demo workspace</p></div></section>',
            unsafe_allow_html=True,
        )
    st.stop()
