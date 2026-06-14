import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.schemas.request_demo import DemoRequest, DemoRequestResponse
from app.services.demo_request_email_service import DemoRequestEmailService


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/request-demo", response_model=DemoRequestResponse)
def request_demo(
    payload: DemoRequest,
    settings: Settings = Depends(get_settings),
) -> DemoRequestResponse:
    try:
        DemoRequestEmailService(settings).send(payload)
    except RuntimeError as exc:
        logger.warning("Demo request email is not configured", extra={"reason": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío de email no está configurado todavía.",
        ) from exc
    except Exception as exc:
        logger.exception("Demo request email failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo enviar la solicitud. Inténtalo de nuevo en unos minutos.",
        ) from exc

    return DemoRequestResponse(
        ok=True,
        message="Solicitud en proceso, nos pondremos en contacto contigo con la mayor brevedad",
    )
