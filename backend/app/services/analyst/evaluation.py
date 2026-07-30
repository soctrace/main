from app.services.analyst.schemas import AnalystChatResponse


def validate_response_grounding(response: AnalystChatResponse) -> list[str]:
    warnings: list[str] = []
    if not response.data_used:
        warnings.append("No hay fuentes internas asociadas a esta respuesta.")
    if not response.methodology.strip():
        warnings.append("La metodologia no esta disponible en esta respuesta.")
    if not response.sections and not response.tables:
        warnings.append("Esta respuesta no incluye evidencia territorial detallada.")
    return warnings
