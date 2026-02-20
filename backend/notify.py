from __future__ import annotations

import json
import urllib.request

from .config import settings


def send_handoff_to_sheets(payload: dict) -> bool:
    url = (settings.SHEETS_WEBHOOK_URL or "").strip()
    secret = (settings.SHEETS_WEBHOOK_SECRET or "").strip()
    if not url or not secret:
        print("[SHEETS] disabled: missing webhook config")
        return False

    payload = dict(payload)
    payload["secret"] = secret

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "dental-agent/1.0"},
        method="POST",
    )

    # Apps Script a veces tarda (cold start). Dale margen + reintentos.
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read() or b""
                text = raw.decode("utf-8", errors="replace")

                ok_http = 200 <= resp.status < 300
                ok_json = False
                try:
                    j = json.loads(text or "{}")
                    ok_json = bool(j.get("ok") is True)
                except Exception:
                    ok_json = False

                ok = bool(ok_http and ok_json)
                print(f"[SHEETS] attempt={attempt} status={resp.status} ok={ok} body={text[:500]}")
                return ok
        except TimeoutError as e:
            print(f"[SHEETS] attempt={attempt} TIMEOUT: {e}")
        except Exception as e:
            print(f"[SHEETS] attempt={attempt} ERROR: {type(e).__name__}: {e}")

    return False


def send_handoff_email(subject: str, body: str) -> bool:
    """
    Envía email vía HTTP (Resend).
    Devuelve True si ok, False si falla. NUNCA debe tumbar el bot.
    """
    api_key = (settings.RESEND_API_KEY or "").strip()
    to = (settings.NOTIFY_EMAIL_TO or "").strip()
    sender = (settings.EMAIL_FROM or "").strip() or "Dental Agent <onboarding@resend.dev>"

    if not (api_key and to):
        print("[EMAIL] disabled: missing RESEND config")
        return False

    payload = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "text": body,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "dental-agent/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
            print(f"[EMAIL] status={resp.status} ok={ok}")
            return ok
    except Exception as e:
        print(f"[EMAIL] ERROR sending email via HTTP: {type(e).__name__}: {e}")
        return False
