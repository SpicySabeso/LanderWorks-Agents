from fastapi.testclient import TestClient

from backend.main import app
from backend.store import reset_state

client = TestClient(app)


def test_twilio_webhook_returns_twiml_and_routes_to_agent():
    sender = "whatsapp:+34600000000"
    reset_state(sender)

    r = client.post(
        "/webhook/twilio",
        data={"Body": "Quiero cita", "From": sender},
    )

    assert r.status_code == 200
    assert "application/xml" in r.headers.get("content-type", "")
    # TwiML básico
    assert "<Response>" in r.text
    assert "<Message>" in r.text
