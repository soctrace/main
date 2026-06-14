from __future__ import annotations

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


def main() -> None:
    session_id = "manual-memory-live"
    questions = [
        "¿Qué secciones concentran más población joven?",
        "¿Son datos de 2025?",
        "¿Cómo lo has calculado?",
    ]
    db = SessionLocal()
    try:
        service = AskSocTraceService(db, get_settings())
        for question in questions:
            response = service.ask(
                AskRequest(
                    question=question,
                    conversationId=session_id,
                    session_id=session_id,
                    activeMunicipality="29070",
                )
            )
            print("\n---")
            print(question)
            print(response.answer)
            print({"conversation_id": response.conversation_id, "session_id": response.session_id})
    finally:
        db.close()


if __name__ == "__main__":
    main()
