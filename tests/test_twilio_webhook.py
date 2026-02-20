from fastapi.testclient import TestClient

import backend.twilio_client as twilio_client
from backend.main import app
from backend.store import reset_state

twilio_client.settings.TWILIO_WHATSAPP_FROM = ""
twilio_client.settings.TWILIO_ACCOUNT_SID = ""
twilio_client.settings.TWILIO_AUTH_TOKEN = ""

client = TestClient(app)


def test_twilio_webhook_returns_200_and_ack():
    sender = "whatsapp:+34600000000"
    reset_state(sender)

    r = client.post(
        "/webhook/twilio",
        data={"Body": "Quiero cita", "From": sender},
    )

    assert r.status_code == 200
    assert r.text == "" or r.text is None
