import logging
import time

from fastapi import APIRouter, Depends

from app.schemas.analyst import AnalystAnswer, AnalystQuestion
from app.core.config import Settings, get_settings
from app.services.analyst import PoliticalAnalystAgent, get_political_analyst_agent
from app.services.analyst.schemas import AnalystChatRequest, AnalystChatResponse
from app.services.local_analyst_service import LocalAnalystService, get_local_analyst_service
from app.services.orchestrator.methodology_interceptor import methodology_interceptor


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AnalystAnswer)
def ask_local_analyst(
    payload: AnalystQuestion,
    analyst: LocalAnalystService = Depends(get_local_analyst_service),
) -> AnalystAnswer:
    return analyst.ask(payload.question, payload.municipality_id)


@router.post("/chat", response_model=AnalystChatResponse)
async def chat_political_analyst(
    payload: AnalystChatRequest,
    analyst: PoliticalAnalystAgent = Depends(get_political_analyst_agent),
    settings: Settings = Depends(get_settings),
) -> AnalystChatResponse:
    started = time.monotonic()
    enabled = settings.enable_methodology_explanation_layer
    handled = False
    question_type = "analytical"
    reason = "feature_disabled"
    error_type = None
    if enabled:
        try:
            methodology_response, classification = methodology_interceptor.try_handle(payload)
            handled = methodology_response is not None
            question_type = classification.question_type
            reason = classification.reason
            if methodology_response is not None:
                logger.info(
                    "methodology_interception",
                    extra={"enabled": True, "handled": True, "question_type": question_type, "reason": reason,
                           "conversation_id": payload.conversation_id,
                           "duration_ms": round((time.monotonic() - started) * 1000, 2),
                           "fallback_to_legacy": False, "error_type": None},
                )
                return methodology_response
        except Exception as exc:
            error_type = type(exc).__name__
            reason = "interceptor_error"
            logger.exception(
                "methodology_interception_failed",
                extra={"enabled": True, "handled": False, "question_type": "ambiguous", "reason": reason,
                       "conversation_id": payload.conversation_id, "fallback_to_legacy": True,
                       "error_type": error_type},
            )

    response = await analyst.chat(payload)
    try:
        methodology_interceptor.remember(payload, response)
    except Exception as exc:
        logger.exception("methodology_context_store_failed", extra={"error_type": type(exc).__name__})
    logger.info(
        "methodology_interception",
        extra={"enabled": enabled, "handled": handled, "question_type": question_type, "reason": reason,
               "conversation_id": payload.conversation_id,
               "duration_ms": round((time.monotonic() - started) * 1000, 2),
               "fallback_to_legacy": True, "error_type": error_type},
    )
    return response
