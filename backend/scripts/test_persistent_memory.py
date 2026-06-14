from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


SESSION_ID = "memory-health-check"


def main() -> int:
    session = SessionLocal()
    try:
        service = AskSocTraceService(session, get_settings())
        first = service.ask(
            AskRequest(
                question="¿Cuál es la sección con mayor población?",
                conversationId=SESSION_ID,
                session_id=SESSION_ID,
                activeMunicipality="29070",
            )
        )
        second = service.ask(
            AskRequest(
                question="¿Son datos de 2025?",
                conversationId=first.conversation_id or SESSION_ID,
                session_id=first.session_id or SESSION_ID,
                activeMunicipality="29070",
            )
        )
        conversation_id = first.conversation_id or second.conversation_id
        if not conversation_id:
            print("Memory failed: no conversation_id returned")
            return 1
        turns = session.execute(
            text("SELECT COUNT(*) FROM core.agent_turns WHERE conversation_id = :conversation_id"),
            {"conversation_id": conversation_id},
        ).scalar_one()
        if turns < 2:
            print(f"Memory failed: only {turns} turns stored")
            return 1
        if "2025" not in second.answer:
            print(f"Follow-up failed: {second.answer}")
            return 1
        print("Memory OK")
        print(f"conversation_id={conversation_id}")
        print(f"turns={turns}")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"Memory failed: {exc}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
