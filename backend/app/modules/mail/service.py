from datetime import datetime, timezone
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Message
from app.modules.mail.templates import render


def _try_smtp(message: Message, to_email: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(message.body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        message.smtp_sent_at = datetime.now(timezone.utc)
        message.smtp_error = None
    except Exception as exc:
        message.smtp_error = str(exc)[:500]


def send_template(
    db: Session,
    *,
    to_user_id: str,
    template_key: str,
    context: dict,
    related_type: str | None = None,
    related_id: str | None = None,
    to_email: str = "",
) -> Message:
    subject, body = render(template_key, context)
    message = Message(
        to_user_id=to_user_id,
        template_key=template_key,
        subject=subject,
        body=body,
        related_type=related_type,
        related_id=related_id,
    )
    db.add(message)
    db.flush()
    _try_smtp(message, to_email)
    db.commit()
    db.refresh(message)
    return message


def retry_smtp(db: Session, message: Message, to_email: str) -> Message:
    _try_smtp(message, to_email)
    db.commit()
    db.refresh(message)
    return message
