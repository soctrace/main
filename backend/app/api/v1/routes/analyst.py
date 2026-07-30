from fastapi import APIRouter, Depends

from app.schemas.analyst import AnalystAnswer, AnalystQuestion
from app.services.analyst import PoliticalAnalystAgent, get_political_analyst_agent
from app.services.analyst.schemas import AnalystChatRequest, AnalystChatResponse
from app.services.local_analyst_service import LocalAnalystService, get_local_analyst_service


router = APIRouter()


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
) -> AnalystChatResponse:
    return await analyst.chat(payload)
