from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _load_catalog() -> tuple[list[tuple[str, list[str]]], dict[str, str]]:
    source = (ROOT / "soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts").read_text()
    tests_block = source.split("const testsByCategory", 1)[1].split("function slugify", 1)[0]
    available_block = source.split("const availablePromptTools", 1)[1].split("function toolForPrompt", 1)[0]
    available = dict(re.findall(r'"([^"]+)": "([^"]+)"', available_block))
    categories: list[tuple[str, list[str]]] = []
    for match in re.finditer(r'\["([^"]+)", \[(.*?)\]\]', tests_block, re.S):
        category = match.group(1)
        prompts = [prompt for prompt, _chart in re.findall(r'\["([^"]+)"\s*,\s*"?([^"\]]*)"?\]', match.group(2))]
        if prompts:
            categories.append((category, prompts))
    return categories, available


def _reason(category: str, prompt: str, available: dict[str, str]) -> str:
    if prompt in available:
        return "Tool Layer v2 executable with current Mijas agent_* data."
    future_reasons = {
        "Prediccion": "Requires probabilistic forecasting or predictive modelling.",
        "Clustering": "Requires dedicated clustering/ML models.",
        "Oportunidades": "Requires campaign optimization model.",
        "Movilizacion": "Requires behavioral mobilization model.",
        "Segmentacion": "Requires voter profile/segmentation model.",
        "Evolucion": "Requires party-specific temporal vote-transfer/evolution logic not exposed in Tool Layer v2.",
    }
    for key, value in future_reasons.items():
        if key in category:
            return value
    lowered = prompt.lower()
    if "transferencia" in lowered or "votante medio" in lowered:
        return "Requires behavioral modelling not implemented."
    return "No reliable deterministic tool recipe exposed for MVP yet."


def main() -> int:
    categories, available = _load_catalog()
    rows: list[tuple[str, str, str, str, str]] = []
    for category, prompts in categories:
        for prompt in prompts:
            tool = available.get(prompt, "-")
            status = "Disponible" if prompt in available else "Próximamente"
            rows.append((category, prompt, tool, status, _reason(category, prompt, available)))

    available_count = sum(1 for row in rows if row[3] == "Disponible")
    audit_lines = [
        "# Ask SocTrace Test Catalog Audit",
        "",
        "Fecha: 2026-06-09.",
        "",
        "Estados visibles del MVP: `Disponible` y `Próximamente`. Los estados internos `supported`, `beta` y `pending` no se exponen en la UI.",
        "",
        f"Resumen: {available_count} de {len(rows)} consultas visibles quedan como `Disponible` ({available_count / len(rows) * 100:.1f}%).",
        "",
        "| Category | Question | Current status | Tool available? | Semantic mapping available? | Dataset available? | Can execute now? | Recommended status | Reason |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for category, prompt, tool, status, reason in rows:
        can_execute = "Sí" if status == "Disponible" else "No"
        semantic = "Sí" if status == "Disponible" else "Parcial/No"
        dataset = "Sí" if status == "Disponible" else "Parcial"
        tool_label = tool if tool != "-" else "No"
        audit_lines.append(
            f"| {category} | {prompt} | legacy | {tool_label} | {semantic} | {dataset} | {can_execute} | {status} | {reason} |"
        )
    (ROOT / "docs/test_catalog_audit.md").write_text("\n".join(audit_lines) + "\n")

    group_rules = {
        "Demografia - Poblacion": "Demografía",
        "Demografia - Edad": "Edad",
        "Demografia - Cohortes": "Edad",
        "Electoral": "Comportamiento Electoral",
        "Ciencia politica": "Comportamiento Electoral",
        "Economia": "Renta",
        "Renta": "Renta",
        "Inmobiliario": "Vivienda",
        "Sociologia": "Inteligencia Territorial",
        "Estadistica": "Inteligencia Territorial",
        "Data Science - Correlaciones": "Inteligencia Territorial",
        "Data Science - Scores": "Inteligencia Territorial",
    }
    grouped: dict[str, list[tuple[str, str, str]]] = {
        "Demografía": [],
        "Edad": [],
        "Comportamiento Electoral": [],
        "Renta": [],
        "Vivienda": [],
        "Inteligencia Territorial": [],
    }
    for category, prompt, tool, status, _reason_text in rows:
        if status != "Disponible":
            continue
        group = next((value for key, value in group_rules.items() if key in category), None)
        if group:
            grouped[group].append((prompt, tool, status))

    available_lines = [
        "# Ask SocTrace Available Test Catalog",
        "",
        "Fecha: 2026-06-09.",
        "",
        "Catálogo interno de consultas marcadas como `Disponible` para Friend & Family MVP. Todas se apoyan en Tool Layer v2 y datasets `marts.agent_*`; la validación smoke se ejecuta con `backend/scripts/validate_mvp_test_catalog.py`.",
        "",
    ]
    for group, items in grouped.items():
        available_lines.extend([f"## {group}", "", "| Question | Tool | Status |", "|---|---|---|"])
        for prompt, tool, status in items:
            available_lines.append(f"| {prompt} | `{tool}` | {status} |")
        available_lines.append("")
    (ROOT / "docs/test_catalog_available.md").write_text("\n".join(available_lines))

    print(f"wrote audit rows={len(rows)} available={available_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
