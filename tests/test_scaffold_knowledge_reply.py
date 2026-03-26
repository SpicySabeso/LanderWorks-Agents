from backend.apps.scaffold_web_agent.chat_service import ChatApplicationService
from backend.apps.scaffold_web_agent.domain import SessionState, Step
from backend.apps.scaffold_web_agent.tenants import Tenant


class DummySessionService:
    def get_state(self, tenant_id, session_id):
        return SessionState()

    def save_state(self, tenant_id, session_id, state):
        pass


class DummyLeadService:
    def create_lead(self, *args, **kwargs):
        pass


class DummyDeliveryService:
    def deliver_lead(self, *args, **kwargs):
        pass


class DummyEventService:
    def record(self, *args, **kwargs):
        pass


class DummyMailer:
    def send(self, *args, **kwargs):
        pass


def test_chat_service_adds_knowledge_to_reply_without_polluting_message(monkeypatch):
    captured = {}

    def fake_handle_user_message(state, message):
        captured["message"] = message
        new_state = SessionState()
        new_state.step = Step.COLLECT_CONTACT
        return (
            new_state,
            "Hi — I can help route your inquiry to our team.\nFirst, what’s your email so we can reply?",
        )

    monkeypatch.setattr(
        "backend.apps.scaffold_web_agent.chat_service.handle_user_message",
        fake_handle_user_message,
    )
    monkeypatch.setattr(
        "backend.apps.scaffold_web_agent.chat_service.is_rate_limited",
        lambda tenant_id, client_ip: False,
    )

    service = ChatApplicationService(
        session_service=DummySessionService(),
        lead_service=DummyLeadService(),
        delivery_service=DummyDeliveryService(),
        event_service=DummyEventService(),
    )

    tenant = Tenant(
        tenant_id="tenant-a",
        widget_token="tok",
        inbox_email="x@example.com",
        subject_prefix="[X]",
        allowed_origins=[],
        agent_type="scaffold_web_agent",
        knowledge_text="We are a scaffolding supplier for international buyers.",
    )

    result = service.process_chat(
        tenant=tenant,
        client_ip="127.0.0.1",
        session_id="sess-1",
        message="I need a quotation",
        mailer=DummyMailer(),
    )

    assert captured["message"] == "I need a quotation"
    assert "We are a scaffolding supplier for international buyers." in result.reply
    assert result.step == "collect_contact"
    assert result.is_done is False
