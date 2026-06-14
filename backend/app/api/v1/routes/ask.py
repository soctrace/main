from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ask.diagnostics import ask_llm_health
from app.ask.conversation import PersistentConversationStore
from app.ask.service import AskSocTraceService, get_ask_soctrace_service
from app.core.config import get_settings
from app.core.database import get_db_session
from app.schemas.ask import AskRequest, AskResponse


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask_soctrace(
    payload: AskRequest,
    service: AskSocTraceService = Depends(get_ask_soctrace_service),
) -> AskResponse:
    return service.ask(payload)


@router.post("/agent/chat", response_model=AskResponse)
def ask_soctrace_agent_chat(
    payload: AskRequest,
    service: AskSocTraceService = Depends(get_ask_soctrace_service),
) -> AskResponse:
    return service.ask(payload)


@router.get("/ask/llm/health")
def llm_health(session: Session = Depends(get_db_session)) -> dict:
    return ask_llm_health(session=session, settings=get_settings())


@router.get("/ask/conversations/{conversation_id}/debug")
def conversation_debug(
    conversation_id: str,
    session: Session = Depends(get_db_session),
) -> dict:
    settings = get_settings()
    if settings.app_env != "development" or not settings.ask_debug_enabled:
        return {"enabled": False}
    store = PersistentConversationStore(session)
    context = store.get_context(conversation_id)
    return {
        "enabled": True,
        "last_context": context.model_dump(),
        "recent_turns": context.recent_turns,
    }
