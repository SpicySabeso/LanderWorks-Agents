# AI Lead Capture SaaS Platform

Multi-tenant SaaS platform that deploys AI-powered lead capture agents on any website with a single `<script>` tag. Features streaming responses (SSE), LLM observability via Langfuse, and is deployed on both AWS EC2 and Azure App Service.

**Portfolio:** [notion.so/Lander-Iglesias-ed9bca668ca08368ab0c81aed0869e1d](https://www.notion.so/Lander-Iglesias-ed9bca668ca08368ab0c81aed0869e1d)  
**Live demo (Azure):** [lander-lead-capture.azurewebsites.net](https://lander-lead-capture.azurewebsites.net)

---

## The problem

Businesses need to capture leads from website visitors 24/7 — but generic chatbots feel robotic, and custom solutions are expensive to build and maintain per client. There's no easy way to deploy a knowledge-trained AI agent on a client's website without code changes, and no visibility into what the agent is doing in production.

---

## Solution

A multi-tenant platform where each client (tenant) gets their own AI agent configured with their business knowledge. The agent is deployed on any website with a single `<script>` tag — no backend changes required. Responses stream progressively like ChatGPT. Every conversation is traced in Langfuse for full LLM observability.

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
    ┌──────┴───────────────────┐
    │              │           │
    ▼              ▼           ▼
Lead captured  SSE stream  Langfuse trace
(email saved)  (chunks →   (tokens, latency,
    │           widget)     metadata logged)
    ▼
Email delivered
via Resend
```

---

## Key features

**Streaming responses (SSE)**
Words appear progressively as Claude generates them — same UX as ChatGPT. Implemented via `StreamingResponse` with `media_type="text/event-stream"` and `X-Accel-Buffering: no` to disable proxy buffering. The lead marker `<<<SEND_LEAD>>>` is detected in the accumulated buffer without ever being shown to the user.

**Multi-tenant isolation**
Each client has their own token, knowledge base, allowed origins, and conversation sessions. One platform, unlimited clients. Tenants are managed via an admin panel — no code changes needed to onboard a new client.

**Single script deployment**
```html
<script src="https://your-domain.com/scaffold-agent/widget.js?token=tok_client_123"></script>
```
Zero backend changes on the client's side.

**Per-tenant Claude agents**
Each tenant's `knowledge_text` is injected as Claude's system prompt. The agent answers as a specialist for that specific business without knowing anything about other tenants.

**LLM Observability with Langfuse**
Every conversation is traced:
- Token usage per message and per session
- Latency tracking per LLM call
- Input/output logged for quality monitoring
- Conversation metadata (tenant, session, lead status)

API correcta en v4.x: `langfuse.trace().generation()` — no `langfuse.decorators` que no existe en esa versión.

**Automatic lead capture**
The agent identifies when a visitor provides their email through natural conversation. The lead is confirmed, saved to SQLite, and delivered to the client via email (Resend).

**Deployed on two clouds**
- **AWS EC2** — t3.micro, eu-west-1, IAM user, CLI configuration
- **Azure App Service** — B1, West Europe, ACR, PaaS managed deployment

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Anthropic Claude Haiku |
| LLM Observability | Langfuse |
| Streaming | Server-Sent Events (SSE) |
| Backend | FastAPI, Python 3.12 |
| Database | SQLite |
| Email delivery | Resend |
| Cloud (AWS) | EC2, IAM |
| Cloud (Azure) | App Service, Container Registry (ACR) |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Code quality | ruff, Black, pytest, gitleaks |

---

## Key technical decisions

**Why SSE instead of WebSockets?**
SSE is unidirectional (server → client) which is exactly what streaming LLM responses need. WebSockets are bidirectional and add unnecessary complexity. SSE works over standard HTTP, is easier to proxy, and FastAPI's `StreamingResponse` supports it natively.

**Why Langfuse for observability?**
Langfuse is the standard LLMOps tool for tracing LLM applications. Token-level visibility without changing the agent's logic. API correcta en v4.x: `langfuse.trace().generation()`.

**Why inject knowledge as system prompt instead of RAG?**
For short business knowledge (services, pricing, FAQs), a system prompt is simpler, faster, and cheaper than a full RAG pipeline. For typical SMB clients, this is the right trade-off.

**AWS vs Azure — key differences learned**
- AWS uses static access keys; Azure uses OAuth interactive login (`az login`)
- Azure Resource Groups have no direct AWS equivalent — they're logical containers for all resources
- Azure App Service requires `WEBSITES_PORT=8000` explicitly — without it, Azure tries port 80 and the container fails
- Azure ACR ≈ AWS ECR for private Docker registries

---

## Limitations

- **Render/SQLite ephemeral storage.** SQLite data is lost on redeploy. Re-create tenants via the admin panel.
- **No conversation memory across sessions.** Each new page load starts fresh.
- **Langfuse latency.** Adds ~50ms per trace. Acceptable for conversational agents.

---

## Deployment

### Azure App Service

```bash
# Login
az login

# Create resource group
az group create --name lander-portfolio-rg --location westeurope

# Create App Service plan (B1 = 1 core, 1.75GB RAM)
az appservice plan create --name lander-plan --resource-group lander-portfolio-rg --sku B1 --is-linux

# Create Container Registry
az acr create --name landerregistry --resource-group lander-portfolio-rg --sku Basic --admin-enabled true

# Build and push image
docker build -t landerregistry.azurecr.io/lead-capture:latest .
docker push landerregistry.azurecr.io/lead-capture:latest

# Create web app
az webapp create --name lander-lead-capture --resource-group lander-portfolio-rg \
  --plan lander-plan --deployment-container-image-name landerregistry.azurecr.io/lead-capture:latest

# Set environment variables (WEBSITES_PORT is critical)
az webapp config appsettings set --name lander-lead-capture \
  --resource-group lander-portfolio-rg \
  --settings WEBSITES_PORT=8000 ANTHROPIC_API_KEY=... RESEND_API_KEY=...
```

### Running locally

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```

---

## Errors resolved

| Error | Cause | Fix |
|---|---|---|
| `ContainerTimeout` on Azure | Doc Intel Agent tried to connect to PostgreSQL at startup — blocked container init | `try/except` around `init_doc_intel_db()` in `main.py` |
| `ModuleNotFoundError: langfuse` | Works locally (installed in venv) but not in Docker (only requirements.txt is installed) | Add `langfuse` to `requirements.txt` |
| Container fails to start on Azure | Azure tries port 80 by default | Set `WEBSITES_PORT=8000` in App Settings |
| `TypeError: 'bool' object is not iterable` | Bug in SSE lead marker filter | Fixed generator logic in `stream_user_message_llm` |

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
| `WEBSITES_PORT` | Azure App Service only — must be 8000 |

---

## Project structure

```
backend/agents/lead_capture_agent/
├── api.py              # FastAPI endpoints — /chat and /chat/stream (SSE)
├── llm_engine.py       # Claude integration + Langfuse + SSE streaming
├── tenant_store.py     # SQLite tenant management
├── session_state.py    # In-memory conversation history
├── lead_store.py       # Lead capture and storage
├── email_service.py    # Resend email delivery
├── admin_panel.py      # Admin UI and API
├── tenant_cors.py      # Per-tenant CORS middleware
└── widget_template.py  # Embeddable widget with ReadableStream SSE consumer
```