from fastapi import APIRouter, Depends

from app.services.orchestrator import SocTraceOrchestrator, get_soctrace_orchestrator
from app.services.orchestrator.response_schema import OrchestratorChatRequest, OrchestratorResponse


router = APIRouter()


@router.post("/chat", response_model=OrchestratorResponse)
async def chat_orchestrator(
    payload: OrchestratorChatRequest,
    orchestrator: SocTraceOrchestrator = Depends(get_soctrace_orchestrator),
) -> OrchestratorResponse:
    return await orchestrator.chat(payload)
