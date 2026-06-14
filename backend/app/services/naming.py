KNOWN_MUNICIPALITIES = {
    "29070": "Mijas",
}


def municipality_name_from_id(municipality_id: str) -> str:
    return KNOWN_MUNICIPALITIES.get(municipality_id, f"Municipality {municipality_id}")


def district_label_from_code(code: str | None) -> str:
    if not code:
        return "District"
    normalized = code.lstrip("0") or "0"
    return f"District {normalized}"

