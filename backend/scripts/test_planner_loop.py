from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


def main() -> int:
    session = SessionLocal()
    try:
        settings = get_settings()
        service = AskSocTraceService(session, settings)
        response = service.ask(
            AskRequest(
                question="¿Cuál es la sección con mayor población?",
                conversationId="planner-loop-health",
                session_id="planner-loop-health",
                activeMunicipality="29070",
                mode="debug" if settings.ask_debug_enabled else None,
            )
        )
        data = response.data if isinstance(response.data, dict) else {}
        print(f"provider={data.get('provider') or settings.llm_provider}")
        print(f"model={data.get('model')}")
        print(f"complexity={data.get('complexity')}")
        print(f"tool={data.get('tool')}")
        print(f"tool_args={data.get('tool_args')}")
        print(f"status={data.get('summary', {}).get('status') or 'ok' if data.get('rows') else 'unknown'}")
        print(f"answer preview={response.answer[:220]}")
        return 0 if data.get("provider") == "gemini" and data.get("tool") else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
