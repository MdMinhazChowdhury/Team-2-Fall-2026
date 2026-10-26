import base64
import hashlib
import json
import smtplib
from email.message import EmailMessage

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from tasktrack.config import settings
from tasktrack.models import Outbox, uuid


def cipher() -> Fernet:
    key = (
        settings().email_key
        or base64.urlsafe_b64encode(
            hashlib.sha256(settings().session_secret.encode()).digest()
        ).decode()
    )
    return Fernet(key.encode())


def queue_mail(
    db: Session, account_id: str, recipient: str, subject: str, body: str, key: str | None = None
) -> None:
    payload = (
        cipher()
        .encrypt(json.dumps({"recipient": recipient, "subject": subject, "body": body}).encode())
        .decode()
    )
    db.add(Outbox(account_id=account_id, delivery_key=key or uuid(), encrypted_payload=payload))


def send_mail(encrypted: str, delivery_key: str) -> None:
    if not settings().email_enabled:
        raise RuntimeError("email_disabled")
    data = json.loads(cipher().decrypt(encrypted.encode()))
    message = EmailMessage()
    message["From"] = settings().email_from
    message["To"] = data["recipient"]
    message["Subject"] = data["subject"]
    message["Message-ID"] = f"<{delivery_key}@tasktrack>"
    message.set_content(data["body"])
    with smtplib.SMTP(settings().smtp_host, settings().smtp_port, timeout=10) as smtp:
        if settings().smtp_tls:
            smtp.starttls()
        if settings().smtp_user:
            smtp.login(settings().smtp_user, settings().smtp_password)
        smtp.send_message(message)
