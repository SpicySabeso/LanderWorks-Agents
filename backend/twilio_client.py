import os

from twilio.rest import Client

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(
            os.environ["TWILIO_ACCOUNT_SID"],
            os.environ["TWILIO_AUTH_TOKEN"],
        )
    return _client


def send_whatsapp_message(to: str, body: str) -> None:
    client = _get_client()
    from_whatsapp = os.environ["TWILIO_WHATSAPP_FROM"]

    client.messages.create(
        from_=from_whatsapp,
        to=to,
        body=body,
    )
