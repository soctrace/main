from __future__ import annotations


def normalize_followups(values: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values or []:
        question = str(value).strip()
        if not question:
            continue
        if not question.startswith("¿"):
            question = "¿" + question.lstrip("¿")
        question = question.rstrip(".?!؟") + "?"
        key = question.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(question)
    return normalized
