from uuid import uuid4

import backend.notify as notify
from backend.agent import respond
from backend.store import get_state, reset_state


class DummySMTP:
    def __init__(self, host, port, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = False
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return None

    def starttls(self):
        self.started_tls = True
        return None

    def login(self, user, pwd):
        self.logged_in = True
        self.user = user
        self.pwd = pwd
        return None

    def send_message(self, msg):
        self.sent.append(msg)
        return None


def _set_settings(monkeypatch, **kwargs):
    # settings es un objeto; parcheamos atributos directamente
    for k, v in kwargs.items():
        monkeypatch.setattr(notify.settings, k, v, raising=False)


def test_send_handoff_email_disabled_if_missing_config(monkeypatch):
    _set_settings(
        monkeypatch,
        SMTP_HOST="",
        SMTP_USER="",
        SMTP_PASS="",
        SMTP_PORT="587",
        SMTP_FROM="",
        NOTIFY_EMAIL_TO="",
    )

    # aunque hubiera SMTP, no debe ni intentarlo si falta config
    monkeypatch.setattr(notify.smtplib, "SMTP", DummySMTP)

    ok = notify.send_handoff_email("subj", "body")
    assert ok is False


def test_handoff_flow_calls_email(monkeypatch):
    sender = f"scenario-email-handoff-{uuid4()}"
    reset_state(sender)

    called = {"n": 0, "subject": None, "body": None}

    def fake_send(subject: str, body: str) -> bool:
        called["n"] += 1
        called["subject"] = subject
        called["body"] = body
        return True

    monkeypatch.setattr(notify, "send_handoff_email", fake_send)

    respond("Quiero cita", sender=sender)
    respond("Lander", sender=sender)
    respond("612345678", sender=sender)
    respond("Limpieza", sender=sender)
    respond("No es urgente", sender=sender)
    respond("Por la tarde", sender=sender)

    st = get_state(sender)
    assert st.step == "handoff"

    assert called["n"] >= 1
    assert "612345678" in (called["body"] or "")
