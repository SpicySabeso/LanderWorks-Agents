# AI WhatsApp Agent for Clinics

Conversational AI agent that handles patient inquiries on WhatsApp. Collects structured information (name, treatment, urgency), manages appointment requests and escalates to a human when needed.

---

## What it does

- Handles real-time WhatsApp conversations with patients
- Collects structured lead data: name, treatment type, urgency level
- Answers frequently asked questions using a RAG pipeline over clinic documents
- Escalates to a human agent when the conversation requires it
- Prevents duplicate message processing (Twilio retry handling)

---

## Architecture

```
WhatsApp → Twilio webhook → FastAPI
                               │
                               ├── RAG pipeline (ChromaDB + OpenAI embeddings)
                               ├── Conversation state (SQLite)
                               ├── Handoff logic (human escalation)
                               └── Email notification (SMTP)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Messaging | Twilio WhatsApp API |
| Backend | Python, FastAPI |
| AI | OpenAI GPT, RAG pipeline |
| Vector store | ChromaDB |
| Database | SQLite |
| Email | SMTP |

---

## Running locally

```bash
# From project root
uvicorn backend.main:app --reload --port 8000

# Expose locally for Twilio webhook (requires ngrok)
ngrok http 8000
# Set webhook URL in Twilio console: https://your-ngrok-url/webhook/twilio
```

---

## Environment variables

```
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
SMTP_HOST=...
SMTP_USER=...
SMTP_PASS=...
```

---

## Running tests

```bash
pytest tests/dental_agent/ -v
```