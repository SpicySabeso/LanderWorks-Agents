from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import settings


def send_handoff_email(subject: str, body: str) -> bool:
    """
    Envía email por SMTP. Devuelve True si envía, False si está deshabilitado
    o falla (NO debe tumbar el bot).
    """
    host = (settings.SMTP_HOST or "").strip()
    user = (settings.SMTP_USER or "").strip()
    pwd = (settings.SMTP_PASS or "").strip()
    to = (settings.NOTIFY_EMAIL_TO or "").strip()

    if not (host and user and pwd and to):
        print("[EMAIL] disabled: missing SMTP config")
        return False

    from_addr = (settings.SMTP_FROM or "").strip() or user

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, int(settings.SMTP_PORT), timeout=10) as s:
            s.ehlo()
            if int(settings.SMTP_PORT) == 587:
                s.starttls()
                s.ehlo()
            s.login(user, pwd)
            s.send_message(msg)
        print("[EMAIL] sent ok:", {"to": to, "subject": subject})
        return True
    except Exception as e:
        print(f"[EMAIL] ERROR sending email via SMTP: {type(e).__name__}: {e}")
        return False
