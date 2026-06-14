from __future__ import annotations

import math


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return v


def format_number_es(value, decimals: int = 0) -> str:
    v = _to_float(value)
    if v is None:
        return ""

    fmt = f"{{:,.{decimals}f}}"
    txt = fmt.format(v)
    return txt.replace(",", "_").replace(".", ",").replace("_", ".")


def format_density(value, decimals: int = 1) -> str:
    v = _to_float(value)
    if v is None:
        return ""
    return f"{format_number_es(v, decimals=decimals)} hab/km²"


def density_level(value) -> str:
    v = _to_float(value)
    if v is None:
        return ""
    if v < 2000:
        return "Muy baja"
    if v < 5000:
        return "Baja"
    if v < 10000:
        return "Media"
    if v < 20000:
        return "Alta"
    return "Muy alta"
