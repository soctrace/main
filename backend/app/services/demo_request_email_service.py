from email.message import EmailMessage
import smtplib

from app.core.config import Settings
from app.schemas.request_demo import DemoRequest


class DemoRequestEmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, request: DemoRequest) -> None:
        if not self.settings.smtp_host or not self.settings.smtp_user or not self.settings.smtp_password:
            raise RuntimeError("SMTP no configurado. Define SMTP_HOST, SMTP_USER y SMTP_PASSWORD.")

        message = EmailMessage()
        message["Subject"] = "Solicitud de Demo"
        message["From"] = self.settings.smtp_from_email or self.settings.smtp_user
        message["To"] = self.settings.demo_request_to_email
        message["Reply-To"] = request.email
        message.set_content(self._body(request))

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)

    def _body(self, request: DemoRequest) -> str:
        return "\n".join(
            [
                "Nueva solicitud de demo gratuita de SocTrace",
                "",
                f"Organización: {request.organization}",
                f"Nombre: {request.firstName}",
                f"Apellidos: {request.lastName}",
                f"Email: {request.email}",
                f"Teléfono: {request.phone or 'No indicado'}",
                f"Sector: {request.sector}",
                "",
                "Motivos de solicitud:",
                request.reasons,
            ]
        )
