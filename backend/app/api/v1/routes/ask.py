import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ask.diagnostics import ask_llm_health
from app.ask.conversation import PersistentConversationStore
from app.ask.service import AskSocTraceService, get_ask_soctrace_service
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.ask import AskRequest, AskResponse
from app.services.analyst.schemas import AnalystChatRequest
from app.services.orchestrator.methodology_interceptor import methodology_interceptor


router = APIRouter()
logger = logging.getLogger(__name__)


def _methodology_ask_response(payload: AskRequest) -> tuple[AskResponse | None, str, str]:
    methodology_response, classification = methodology_interceptor.try_handle(
        AnalystChatRequest(
            message=payload.question or "",
            conversation_id=payload.conversationId or payload.session_id,
            municipality_id=payload.activeMunicipality or "29070",
            context={
                "active_layer": payload.activeLayer,
                "active_year": payload.activeYear,
                "selected_section_id": payload.selectedSectionId,
            },
        )
    )
    if methodology_response is None:
        return None, classification.question_type, classification.reason

    conversation_id = methodology_response.conversation_id
    return (
        AskResponse(
            answer=methodology_response.answer,
            mode="simple",
            confidence=methodology_response.confidence,
            resultType="methodology",
            entities=[],
            data={"methodology": True, "evidence": []},
            methodology=methodology_response.methodology,
            caveats=list(methodology_response.limitations),
            sources=[],
            suggestedFollowUps=list(methodology_response.follow_up_questions),
            suggested_questions=list(methodology_response.follow_up_questions),
            table=None,
            chartSpec=None,
            conversation_id=conversation_id,
            session_id=payload.session_id or conversation_id,
        ),
        classification.question_type,
        classification.reason,
    )


@router.post("/ask", response_model=AskResponse)
def ask_soctrace(
    payload: AskRequest,
    service: AskSocTraceService = Depends(get_ask_soctrace_service),
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    started = time.monotonic()
    if settings.enable_methodology_explanation_layer:
        try:
            response, question_type, reason = _methodology_ask_response(payload)
            if response is not None:
                logger.info(
                    "methodology_interception",
                    extra={
                        "enabled": True,
                        "handled": True,
                        "entrypoint": "ask",
                        "question_type": question_type,
                        "reason": reason,
                        "conversation_id": response.conversation_id,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                        "fallback_to_legacy": False,
                        "error_type": None,
                    },
                )
                return response
            logger.info(
                "methodology_interception",
                extra={
                    "enabled": True,
                    "handled": False,
                    "entrypoint": "ask",
                    "question_type": question_type,
                    "reason": reason,
                    "conversation_id": payload.conversationId or payload.session_id,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "fallback_to_legacy": True,
                    "error_type": None,
                },
            )
        except Exception as exc:
            logger.exception(
                "methodology_interception_failed",
                extra={
                    "enabled": True,
                    "handled": False,
                    "entrypoint": "ask",
                    "question_type": "ambiguous",
                    "reason": "interceptor_error",
                    "conversation_id": payload.conversationId or payload.session_id,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "fallback_to_legacy": True,
                    "error_type": type(exc).__name__,
                },
            )
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
