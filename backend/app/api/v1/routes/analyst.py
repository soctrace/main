from fastapi import APIRouter, Depends

from app.schemas.analyst import AnalystAnswer, AnalystQuestion
from app.services.local_analyst_service import LocalAnalystService, get_local_analyst_service


router = APIRouter()


@router.post("/ask", response_model=AnalystAnswer)
def ask_local_analyst(
    payload: AnalystQuestion,
    analyst: LocalAnalystService = Depends(get_local_analyst_service),
) -> AnalystAnswer:
    return analyst.ask(payload.question, payload.municipality_id)

