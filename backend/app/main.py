import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.ask import router as ask_router
from app.api.v1.routes.request_demo import router as request_demo_router
from app.ask.diagnostics import diagnostics_banner
from app.core.config import get_settings
from app.core.database import SessionLocal, database_diagnostics


settings = get_settings()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(ask_router, prefix="/api", tags=["ask-soctrace"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(request_demo_router, prefix="/api", tags=["request-demo"])


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def log_ai_agent_diagnostics() -> None:
    db_diag = database_diagnostics()
    logging.getLogger(__name__).info(
        "Database startup diagnostics: DATABASE_URL exists=%s driver=%s host=%s database=%s parse_error=%s",
        db_diag["database_url_exists"],
        db_diag["driver"],
        db_diag["host"],
        db_diag["database"],
        db_diag["url_parse_error"],
    )
    session = SessionLocal()
    try:
        logging.getLogger(__name__).info("\n%s", diagnostics_banner(session=session, settings=settings))
    finally:
        session.close()
