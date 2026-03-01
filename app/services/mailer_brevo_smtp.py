from email.message import EmailMessage

import aiosmtplib
from tenacity import retry, stop_after_attempt, wait_exponential

from app.settings import get_settings


class BrevoMailer:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    async def send_plain_text(self, subject: str, body: str, recipient: str | None = None) -> None:
        settings = get_settings()
        to_addr = recipient or settings.mail_to

        message = EmailMessage()
        message["From"] = settings.mail_from
        message["To"] = to_addr
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_user,
            password=settings.smtp_pass,
        )
