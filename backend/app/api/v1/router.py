from fastapi import APIRouter

from app.api.v1.routes import analytics, analyst, ask, elections, forecasts, geo, metadata, municipalities, request_demo, sections


api_router = APIRouter()
api_router.include_router(geo.router, prefix="/geo", tags=["geo"])
api_router.include_router(sections.router, prefix="/sections", tags=["sections"])
api_router.include_router(
    municipalities.router, prefix="/municipalities", tags=["municipalities"]
)
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
api_router.include_router(forecasts.router, prefix="/forecasts", tags=["forecasts"])
api_router.include_router(elections.router, prefix="/elections", tags=["elections"])
api_router.include_router(analyst.router, prefix="/analyst", tags=["local-analyst"])
api_router.include_router(ask.router, tags=["ask-soctrace"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(request_demo.router, tags=["request-demo"])
