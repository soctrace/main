from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import plotly.graph_objects as go
import streamlit as st

from services.config import get_project_name


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_EXTENSIONS = {".png", ".svg", ".jpg", ".jpeg", ".webp", ".ico"}
ASSET_DIRS = (
    PROJECT_ROOT / "branding",
    PROJECT_ROOT / "assets",
    PROJECT_ROOT / "app" / "assets",
    PROJECT_ROOT / "docs" / "branding",
    PROJECT_ROOT / "data" / "branding",
)

SOCTRACE_SEQUENCE = ["#49E3A7", "#79B8FF", "#F5B85C", "#9D7BFF", "#7CF3FF", "#FF7A9D"]
SOCTRACE_CONTINUOUS_SCALE = [
    [0.0, "#1A1B23"],
    [0.2, "#222436"],
    [0.4, "#2B2E49"],
    [0.6, "#3C4066"],
    [0.8, "#6167A8"],
    [1.0, "#8B92F8"],
]


def _iter_asset_files() -> Iterable[Path]:
    for base_dir in ASSET_DIRS:
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS:
                yield path


def _pick_asset(paths: list[Path], keywords: tuple[str, ...]) -> Path | None:
    if not paths:
        return None

    def score(path: Path) -> tuple[int, int, str]:
        name = path.name.lower()
        keyword_hits = sum(1 for keyword in keywords if keyword in name)
        preferred_ext = 1 if path.suffix.lower() in {".svg", ".png", ".webp"} else 0
        return (keyword_hits, preferred_ext, name)

    ordered = sorted(paths, key=score, reverse=True)
    best = ordered[0]
    if score(best)[0] == 0:
        return None
    return best


@lru_cache(maxsize=1)
def get_brand_assets() -> dict[str, object]:
    files = list(_iter_asset_files())
    logo = _pick_asset(files, ("logo", "logotipo", "brand"))
    icon = _pick_asset(files, ("favicon", "icon", "isotipo", "mark"))
    mockup = _pick_asset(files, ("mockup", "cover", "hero", "device"))
    return {
        "logo": logo,
        "icon": icon or logo,
        "mockup": mockup,
        "all": files,
    }


def configure_page(
    page_title: str,
    *,
    hide_sidebar: bool = False,
    render_sidebar: bool = True,
) -> dict[str, object]:
    assets = get_brand_assets()
    page_icon = str(assets["icon"]) if assets["icon"] else "ST"
    st.set_page_config(
        page_title=f"{page_title} | {get_project_name().upper()}",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="collapsed" if hide_sidebar else "expanded",
    )
    apply_global_styles(hide_sidebar=hide_sidebar)
    if render_sidebar:
        render_sidebar_brand()
    return assets


def apply_global_styles(*, hide_sidebar: bool = False) -> None:
    sidebar_css = ""
    if hide_sidebar:
        sidebar_css = """
        [data-testid="stSidebar"] {
            display: none;
        }

        [data-testid="collapsedControl"] {
            display: none;
        }
        """
    styles = """
        <style>
        :root {
            --soc-bg: #08090D;
            --soc-bg-2: #0F1016;
            --soc-panel: rgba(18, 19, 28, 0.90);
            --soc-panel-strong: rgba(15, 16, 23, 0.96);
            --soc-panel-soft: rgba(24, 25, 36, 0.86);
            --soc-border: rgba(255, 255, 255, 0.08);
            --soc-grid: rgba(255, 255, 255, 0.03);
            --soc-shadow: 0 22px 50px rgba(0, 0, 0, 0.34);
            --soc-text: #F5F7FB;
            --soc-muted: #9CA3B5;
            --soc-accent: #8B92F8;
            --soc-accent-2: #6E77F5;
            --soc-accent-3: #A5ACFF;
            --soc-radius-lg: 18px;
            --soc-radius-md: 14px;
            --soc-radius-sm: 10px;
        }

        html, body, [class*="css"] {
            font-family: "Inter", "Segoe UI", "Helvetica Neue", sans-serif;
        }

        .stApp {
            color: var(--soc-text);
            background:
                radial-gradient(circle at top left, rgba(110, 119, 245, 0.09), transparent 22%),
                radial-gradient(circle at top right, rgba(139, 146, 248, 0.06), transparent 18%),
                linear-gradient(180deg, #08090D 0%, #0A0B10 52%, #0D0F16 100%);
        }

        [data-testid="stAppViewContainer"] {
            background:
                linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
            background-size: 48px 48px;
        }

        [data-testid="stHeader"] {
            background: rgba(8, 9, 13, 0.72);
            backdrop-filter: blur(18px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(11, 12, 18, 0.99) 0%, rgba(13, 14, 21, 0.99) 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }

        [data-testid="stSidebar"] * {
            color: var(--soc-text);
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        __SIDEBAR_CSS__

        .block-container {
            padding-top: 1.55rem;
            padding-bottom: 2.25rem;
            max-width: 1600px;
        }

        h1, h2, h3, h4 {
            color: var(--soc-text);
            letter-spacing: -0.03em;
            font-weight: 600;
        }

        p, li, label, .stCaption, div[data-testid="stMarkdownContainer"] {
            color: var(--soc-text);
        }

        .st-emotion-cache-1wivap2, .st-emotion-cache-pkbazv {
            color: var(--soc-muted);
        }

        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stNumberInput > div > div,
        .stTextInput > div > div,
        .stDateInput > div > div,
        .stTextArea textarea {
            background: rgba(20, 21, 31, 0.96);
            color: var(--soc-text);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
        }

        .stRadio > div,
        .stCheckbox {
            background: transparent;
        }

        [data-testid="stRadio"] label {
            background: rgba(26, 27, 39, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            padding: 0.52rem 0.72rem;
            margin-bottom: 0.42rem;
        }

        [data-testid="stRadio"] label:hover {
            border-color: rgba(139, 146, 248, 0.28);
            background: rgba(31, 33, 48, 0.96);
        }

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            border-radius: 10px;
            min-height: 2.85rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(135deg, rgba(25, 26, 37, 0.98), rgba(18, 19, 29, 0.98));
            color: var(--soc-text);
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stFormSubmitButton > button:hover {
            border-color: rgba(139, 146, 248, 0.28);
            color: #FFFFFF;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background: linear-gradient(135deg, rgba(110, 119, 245, 0.98), rgba(139, 146, 248, 0.98));
            color: #FFFFFF;
            border-color: rgba(139, 146, 248, 0.22);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stPlotlyChart"] {
            background: var(--soc-panel);
            border: 1px solid rgba(255, 255, 255, 0.07);
            box-shadow: var(--soc-shadow);
            border-radius: var(--soc-radius-md);
            padding: 0.4rem;
        }

        .soc-sidebar-brand {
            padding: 0.15rem 0 1rem;
        }

        .soc-sidebar-badge {
            display: inline-block;
            padding: 0.34rem 0.62rem;
            border-radius: 999px;
            background: rgba(110, 119, 245, 0.12);
            border: 1px solid rgba(139, 146, 248, 0.18);
            color: var(--soc-accent);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .soc-sidebar-nav {
            margin-top: 1.2rem;
            display: grid;
            gap: 0.24rem;
        }

        .soc-sidebar-section {
            margin-top: 1rem;
            margin-bottom: 0.45rem;
            color: var(--soc-muted);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            padding: 0.55rem 0.72rem;
            border-radius: 10px;
            color: var(--soc-text);
            text-decoration: none;
            border: 1px solid transparent;
            background: transparent;
        }

        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.05);
        }

        .soc-sidebar-placeholder {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.58rem 0.72rem;
            border-radius: 10px;
            color: var(--soc-text);
            background: transparent;
            border: 1px solid transparent;
        }

        .soc-sidebar-placeholder:hover {
            background: rgba(255, 255, 255, 0.04);
        }

        .soc-sidebar-placeholder span:last-child {
            color: var(--soc-muted);
            font-size: 0.76rem;
        }

        .soc-page-head {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.2rem;
        }

        .soc-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.28rem 0.58rem;
            border-radius: 999px;
            border: 1px solid rgba(139, 146, 248, 0.16);
            background: rgba(110, 119, 245, 0.12);
            color: var(--soc-accent);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .soc-section-head {
            margin-bottom: 1.1rem;
        }

        .soc-section-head h1 {
            margin: 0.48rem 0 0.24rem;
            font-size: 2rem;
        }

        .soc-section-head p {
            margin: 0;
            color: var(--soc-muted);
            max-width: 66rem;
            line-height: 1.6;
        }

        .soc-terminal-hero,
        .soc-panel,
        .soc-metric-card,
        .soc-nav-card,
        .soc-side-panel,
        .soc-detail-panel {
            position: relative;
            overflow: hidden;
            background: var(--soc-panel);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: var(--soc-radius-lg);
            box-shadow: var(--soc-shadow);
        }

        .soc-terminal-hero::before,
        .soc-panel::before,
        .soc-side-panel::before,
        .soc-detail-panel::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 28%);
        }

        .soc-terminal-hero {
            padding: 1.2rem 1.25rem;
            margin-bottom: 1rem;
            background:
                radial-gradient(circle at top right, rgba(110, 119, 245, 0.10), transparent 34%),
                linear-gradient(180deg, rgba(17, 18, 25, 0.98), rgba(13, 14, 20, 0.96));
        }

        .soc-terminal-hero h1 {
            margin: 0.72rem 0 0.42rem;
            font-size: 2rem;
            line-height: 1.05;
        }

        .soc-terminal-hero p {
            margin: 0;
            max-width: 62rem;
            color: var(--soc-muted);
            line-height: 1.6;
        }

        .soc-terminal-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1rem;
        }

        .soc-metric-card {
            padding: 1rem 1.05rem 0.95rem;
            min-height: 122px;
            background: linear-gradient(180deg, rgba(23, 24, 35, 0.94), rgba(18, 19, 28, 0.96));
        }

        .soc-metric-label {
            color: var(--soc-muted);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .soc-metric-value {
            margin-top: 0.52rem;
            color: #FFFFFF;
            font-size: 1.8rem;
            line-height: 1;
            font-weight: 650;
            letter-spacing: -0.04em;
        }

        .soc-metric-help {
            margin-top: 0.55rem;
            color: var(--soc-muted);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .soc-nav-card {
            padding: 1rem 1.05rem;
            min-height: 160px;
            background: linear-gradient(180deg, rgba(21, 22, 31, 0.96), rgba(17, 18, 26, 0.96));
        }

        .soc-nav-kicker {
            color: var(--soc-accent-2);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .soc-nav-card h3 {
            margin: 0.55rem 0 0.42rem;
            font-size: 1.02rem;
        }

        .soc-nav-card p {
            margin: 0;
            color: var(--soc-muted);
            line-height: 1.55;
        }

        .soc-side-panel,
        .soc-detail-panel {
            padding: 1rem 1rem 1.05rem;
            background: linear-gradient(180deg, rgba(17, 18, 26, 0.97), rgba(14, 15, 22, 0.97));
        }

        .soc-panel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.85rem;
        }

        .soc-panel-title h3 {
            margin: 0;
            font-size: 1rem;
        }

        .soc-panel-title p {
            margin: 0.25rem 0 0;
            color: var(--soc-muted);
            font-size: 0.9rem;
        }

        .soc-map-shell {
            padding: 0.55rem;
            border-radius: 18px;
            background:
                linear-gradient(180deg, rgba(18, 19, 28, 0.98), rgba(14, 15, 22, 0.98));
            border: 1px solid rgba(255, 255, 255, 0.07);
            box-shadow: var(--soc-shadow);
        }

        .soc-map-caption {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0 0.35rem 0.75rem;
        }

        .soc-map-caption p {
            margin: 0;
            color: var(--soc-muted);
            font-size: 0.92rem;
        }

        .soc-kpi-inline {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-bottom: 0.8rem;
        }

        .soc-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.38rem 0.62rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.07);
            background: rgba(31, 33, 48, 0.85);
            color: var(--soc-text);
            font-size: 0.78rem;
        }

        .soc-layer-note {
            margin-top: 0.55rem;
            color: var(--soc-muted);
            font-size: 0.86rem;
            line-height: 1.55;
        }

        .soc-detail-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.7rem;
            margin-top: 0.9rem;
        }

        .soc-detail-item {
            padding: 0.8rem 0.85rem;
            border-radius: 12px;
            background: rgba(24, 25, 36, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .soc-detail-item span {
            display: block;
        }

        .soc-detail-item .label {
            color: var(--soc-muted);
            font-size: 0.74rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .soc-detail-item .value {
            margin-top: 0.45rem;
            color: #FFFFFF;
            font-size: 0.98rem;
            line-height: 1.35;
            font-weight: 600;
        }

        .soc-mini-note {
            color: var(--soc-muted);
            font-size: 0.84rem;
            line-height: 1.55;
        }

        .soc-collapse-rail {
            display: flex;
            align-items: start;
            justify-content: center;
            padding-top: 2.3rem;
        }

        .soc-auth-stage {
            display: flex;
            justify-content: center;
            padding-top: 1.15rem;
        }

        .soc-auth-stack {
            width: min(100%, 188px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            transform: translateY(0);
        }

        .soc-auth-shell {
            width: 100%;
        }

        .soc-auth-logo {
            display: flex;
            justify-content: center;
        }

        .soc-auth-logo-image,
        .soc-auth-logo-fallback {
            width: min(146px, 34vw);
            height: auto;
            opacity: 0.9;
            filter: drop-shadow(0 10px 22px rgba(0, 0, 0, 0.28));
        }

        .soc-auth-logo-fallback {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            aspect-ratio: 1;
            border-radius: 28px;
            background: rgba(255, 255, 255, 0.03);
            color: rgba(255, 255, 255, 0.72);
            font-size: 2.3rem;
            font-weight: 700;
            letter-spacing: -0.08em;
        }

        .soc-auth-form {
            width: 100%;
            margin: 0.62rem auto 0;
            padding: 0;
        }

        div[data-testid="stForm"] {
            border: none;
            background: transparent;
            padding: 0;
            box-shadow: none;
        }

        div[data-testid="stForm"] > div {
            border: none;
            padding: 0;
        }

        .soc-auth-form [data-testid="stVerticalBlock"] {
            gap: 0.3rem;
        }

        .soc-auth-form .stTextInput {
            margin-bottom: 0;
        }

        .soc-auth-form .stTextInput > div {
            width: 100%;
        }

        .soc-auth-form .stTextInput > div > div {
            width: 100%;
            border-radius: 9px;
            background: rgba(15, 16, 23, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.045);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.14);
            box-sizing: border-box;
        }

        .soc-auth-form .stTextInput input,
        .soc-auth-form input[type="text"],
        .soc-auth-form input[type="password"] {
            width: 100%;
            box-sizing: border-box;
            min-height: 1.76rem;
            padding: 0 0.54rem;
            font-size: 0.78rem;
            line-height: 1.15;
            font-family: inherit;
        }

        .soc-auth-form .stTextInput input[type="password"] {
            padding-right: 0.54rem;
        }

        .soc-auth-form .stTextInput input::placeholder,
        .soc-auth-form input[type="text"]::placeholder,
        .soc-auth-form input[type="password"]::placeholder {
            color: rgba(156, 163, 181, 0.7);
        }

        .soc-auth-form input[type="password"]::-ms-reveal,
        .soc-auth-form input[type="password"]::-ms-clear {
            display: none;
        }

        .soc-auth-form .stFormSubmitButton {
            display: flex;
            justify-content: flex-end;
            margin-top: 0.08rem;
        }

        .soc-auth-form .stFormSubmitButton > button {
            width: 74px;
            min-height: 1.68rem;
            padding: 0 0.42rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 500;
            letter-spacing: 0.01em;
            color: rgba(245, 247, 251, 0.62);
            box-shadow: 0 5px 12px rgba(0, 0, 0, 0.14);
        }

        .soc-auth-footer {
            margin-top: 0.68rem;
            text-align: center;
            color: var(--soc-muted);
            font-size: 0.68rem;
        }

        .soc-map-shell--immersive {
            min-height: calc(100vh - 8rem);
            padding: 0.45rem;
        }

        .soc-map-toolbar {
            display: flex;
            justify-content: flex-end;
            padding: 0.2rem 0.2rem 0.6rem;
        }

        .soc-map-toolbar-note {
            display: inline-flex;
            align-items: center;
            padding: 0.55rem 0.78rem;
            border-radius: 999px;
            color: var(--soc-muted);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 0.78rem;
            line-height: 1;
        }

        .soc-popover-body {
            margin: 0 0 0.85rem;
            color: var(--soc-muted);
            font-size: 0.86rem;
            line-height: 1.55;
        }

        @media (max-width: 1100px) {
            .soc-terminal-grid,
            .soc-detail-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 780px) {
            .soc-auth-stack {
                width: min(100%, 178px);
            }

            .soc-auth-logo-image,
            .soc-auth-logo-fallback {
                width: min(136px, 42vw);
            }

            .soc-auth-form {
                margin-top: 0.56rem;
            }

            .soc-auth-form .stTextInput input {
                min-height: 1.72rem;
            }

            .soc-auth-form .stFormSubmitButton > button {
                width: 70px;
                min-height: 1.62rem;
            }

            .soc-terminal-grid,
            .soc-detail-grid {
                grid-template-columns: repeat(1, minmax(0, 1fr));
            }
        }
        </style>
        """
    st.markdown(styles.replace("__SIDEBAR_CSS__", sidebar_css), unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    assets = get_brand_assets()
    st.sidebar.markdown('<div class="soc-sidebar-brand">', unsafe_allow_html=True)
    if assets["logo"]:
        st.sidebar.image(str(assets["logo"]), use_container_width=True)
    else:
        st.sidebar.markdown(
            f'<div class="soc-sidebar-badge">{get_project_name().upper()}</div>',
            unsafe_allow_html=True,
        )
    st.sidebar.caption("Territorial intelligence platform")
    st.sidebar.markdown('<div class="soc-sidebar-section">Workspace</div>', unsafe_allow_html=True)
    st.sidebar.page_link("Home.py", label="Home", icon=":material/home:")
    st.sidebar.page_link("pages/01_Mapa.py", label="Mapa", icon=":material/map:")
    st.sidebar.page_link("pages/03_Comparador.py", label="Insights", icon=":material/insights:")
    st.sidebar.markdown(
        '<div class="soc-sidebar-placeholder"><span>Chat AI</span><span>Soon</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="soc-sidebar-placeholder"><span>Settings</span><span>Beta</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def render_section_header(title: str, description: str, eyebrow: str = "SocTrace") -> None:
    st.markdown(
        f"""
        <div class="soc-section-head">
            <div class="soc-eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: list[dict[str, str]], columns: int | None = None) -> None:
    if not metrics:
        return

    n_cols = columns or len(metrics)
    cols = st.columns(n_cols)
    for idx, metric in enumerate(metrics):
        with cols[idx % n_cols]:
            st.markdown(
                f"""
                <div class="soc-metric-card">
                    <div class="soc-metric-label">{metric["label"]}</div>
                    <div class="soc-metric-value">{metric["value"]}</div>
                    <div class="soc-metric-help">{metric.get("help", "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_nav_cards(cards: list[dict[str, str]]) -> None:
    cols = st.columns(len(cards))
    for idx, card in enumerate(cards):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="soc-nav-card">
                    <div class="soc-nav-kicker">{card["kicker"]}</div>
                    <h3>{card["title"]}</h3>
                    <p>{card["body"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def get_detected_asset_paths() -> list[str]:
    return [str(path.relative_to(PROJECT_ROOT)) for path in get_brand_assets()["all"]]


def apply_plotly_branding(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=SOCTRACE_SEQUENCE,
        font={"family": '"Space Grotesk, Segoe UI, sans-serif"', "color": "#E6F0F8"},
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(124, 243, 255, 0.09)", zeroline=False)
    return fig
