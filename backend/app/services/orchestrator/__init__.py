from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.services.orchestrator.orchestrator import SocTraceOrchestrator


def get_soctrace_orchestrator(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SocTraceOrchestrator:
    return SocTraceOrchestrator(session=session, settings=settings)


__all__ = ["SocTraceOrchestrator", "get_soctrace_orchestrator"]
