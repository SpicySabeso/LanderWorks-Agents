# AI Lead Capture SaaS Platform

Multi-tenant SaaS platform that deploys AI-powered lead capture agents on any website with a single `<script>` tag. Each client gets their own isolated agent trained on their business knowledge, with automatic lead capture, email delivery, and full LLM observability via Langfuse.

**Portfolio:** [notion.so/Lander-Iglesias-ed9bca668ca08368ab0c81aed0869e1d](https://www.notion.so/Lander-Iglesias-ed9bca668ca08368ab0c81aed0869e1d)

---

## The problem

Businesses need to capture leads from website visitors 24/7 — but generic chatbots feel robotic, and custom solutions are expensive to build and maintain per client. There's no easy way to deploy a knowledge-trained AI agent on a client's website without code changes, and no visibility into what the agent is actually doing in production.

---

## Solution

A multi-tenant platform where each client (tenant) gets their own AI agent configured with their business knowledge. The agent is deployed on any website with a single `<script>` tag — no backend changes required. Every conversation is traced in Langfuse for full LLM observability.

---

## Architecture

```
Client website (any domain)
       │
       ▼
  <script> widget tag
       │
       ▼
  FastAPI backend
       │
  ┌────┴────────────────────┐
  │                         │
  ▼                         ▼
Token validation      Tenant lookup (SQLite)
  │                         │
  └────────┬────────────────┘
           │
    knowledge_text injected
    as Claude system prompt
           │
           ▼
      Claude Haiku
  (tenant-specific agent)
           │
    ┌──────┴──────────┐
    │                 │
    ▼                 ▼
Lead captured    Langfuse trace
(email saved)    (tokens, latency,
    │             metadata logged)
    ▼
Email delivered
via Resend
```

---

## Key features

**Multi-tenant isolation**
Each client has their own token, knowledge base, allowed origins, and conversation sessions. One platform, unlimited clients. Tenants are managed via an admin panel — no code changes needed to onboard a new client.

**Single script deployment**
```html
<script src="https://your-domain.com/scaffold-agent/widget.js?token=tok_client_123"></script>
```
The widget loads automatically on any website with zero backend changes on the client's side.

**Per-tenant Claude agents**
Each tenant's `knowledge_text` is injected as Claude's system prompt. The agent answers as a specialist for that specific business — services, pricing, hours, FAQs — without knowing anything about other tenants.

**LLM Observability with Langfuse**
Every conversation is traced in Langfuse:
- Token usage per message and per session
- Latency tracking per LLM call
- Input/output logged for quality monitoring
- Conversation metadata (tenant, session, lead status)

This is what separates a prototype from a production system — you can't improve what you can't measure.

**Automatic lead capture**
The agent identifies when a visitor provides their email through natural conversation. The lead is confirmed, saved to SQLite, and delivered to the client via email (Resend).

**Admin panel**
Tenant management, per-tenant analytics, token rotation and revocation, session and lead inspection.

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude Haiku |
| LLM Observability | Langfuse |
| Backend | FastAPI, Python 3.12 |
| Database | SQLite |
| Email delivery | Resend |
| Deployment | Render |
| CI/CD | GitHub Actions |
| Code quality | ruff, Black, pytest, gitleaks |

---

## Key technical decisions

**Why Langfuse for observability?**
Langfuse is the standard LLMOps tool for tracing LLM applications. It gives token-level visibility without changing the agent's logic. The API in v4.x: `langfuse.trace().generation()` — not `langfuse.decorators` which doesn't exist in that version.

**Why inject knowledge as system prompt instead of RAG?**
For short business knowledge (services, pricing, FAQs), a system prompt is simpler, faster, and cheaper than a full RAG pipeline. RAG makes sense when the knowledge base is too large to fit in a prompt. For typical SMB clients, the system prompt approach is the right trade-off.

**Why token-based auth instead of OAuth?**
The widget runs on third-party websites that don't share a session with our backend. Tokens are simple, stateless, and easy to rotate without requiring the client to change their embed code.

**Why SQLite instead of PostgreSQL?**
This agent runs on Render's free tier where the filesystem is ephemeral. SQLite is sufficient for the load. For production at scale, migration to PostgreSQL is straightforward via SQLAlchemy.

---

## Limitations

- **Render ephemeral storage.** SQLite data is lost on redeploy. Re-create tenants via the admin panel after redeploy.
- **No conversation memory across sessions.** Each new page load starts a fresh conversation.
- **Langfuse adds ~50ms latency per trace.** Acceptable for conversational agents. Can be made async if needed.

---

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, RESEND_API_KEY, ADMIN_TOKEN,
#          LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

uvicorn backend.main:app --reload --port 8000
```

---

## Environment variables

| Variable | Required for |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Haiku calls |
| `RESEND_API_KEY` | Email delivery |
| `ADMIN_TOKEN` | Admin panel access |
| `LANGFUSE_PUBLIC_KEY` | Langfuse tracing |
| `LANGFUSE_SECRET_KEY` | Langfuse tracing |
| `LANGFUSE_HOST` | Langfuse endpoint (default: cloud.langfuse.com) |

---

## Project structure

```
backend/agents/lead_capture_agent/
├── api.py              # FastAPI endpoints and widget serving
├── llm_engine.py       # Claude integration + Langfuse tracing
├── tenant_store.py     # SQLite tenant management
├── session_state.py    # In-memory conversation history
├── lead_store.py       # Lead capture and storage
├── email_service.py    # Resend email delivery
├── admin_panel.py      # Admin UI and API
└── tenant_cors.py      # Per-tenant CORS middleware
```
