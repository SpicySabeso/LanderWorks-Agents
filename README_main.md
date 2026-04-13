# AI Portfolio — Lander Iglesias

Production-ready AI agents built to demonstrate real-world AI engineering skills. Each project is deployed, documented, and includes tests.

**Stack:** Python · FastAPI · LangChain · Claude (Anthropic) · OpenAI · ChromaDB · SQLite · Render

---

## Agents

### 1. AI WhatsApp Agent for Clinics
Conversational AI agent that handles patient inquiries on WhatsApp, collects structured information and helps clinics manage appointment requests automatically.

**Tech:** Python · FastAPI · Twilio · OpenAI · RAG · ChromaDB  
**[View project →](backend/agents/dental_agent/)**

---

### 2. AI Lead Capture SaaS Platform
Multi-tenant SaaS platform that deploys custom AI agents on any website with a single `<script>` tag. Each client gets their own agent trained on their business knowledge, with automatic lead capture and email delivery.

**Tech:** Python · FastAPI · Claude Haiku · SQLite · Resend · Render  
**[View project →](backend/agents/scaffold_web_agent/)**  
**[Live demo →](https://dental-agent-bn18.onrender.com/scaffold-agent/demo?token=tok_synapse_demo_001)**

---

### 3. RAG PDF Chat Agent
Conversational agent that answers questions about PDF documents using Retrieval-Augmented Generation. Supports conversation history, expandable cited sources, and a compare mode to query two PDFs simultaneously.

**Tech:** Python · FastAPI · LangChain · Claude Haiku · OpenAI Embeddings · ChromaDB  
**[View project →](backend/agents/rag_pdf_agent/)**

---

## Repository structure

```
backend/
├── main.py                        # FastAPI app entrypoint
└── agents/
    ├── dental_agent/              # WhatsApp agent for clinics
    ├── scaffold_web_agent/        # Multi-tenant lead capture SaaS
    └── rag_pdf_agent/             # RAG PDF chat agent
tests/
├── dental_agent/
├── scaffold_web_agent/
└── rag_pdf_agent/
scripts/                           # CLI utilities
```

---

## Running locally

```bash
git clone https://github.com/tu-usuario/ai-portfolio.git
cd ai-portfolio
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn backend.main:app --reload --port 8000
```

---

## Environment variables

| Variable | Required for |
|---|---|
| `ANTHROPIC_API_KEY` | Scaffold agent + RAG agent (Claude) |
| `OPENAI_API_KEY` | RAG agent (embeddings) + Dental agent |
| `ADMIN_TOKEN` | Scaffold agent admin panel |
| `RESEND_API_KEY` | Scaffold agent email delivery |

---

## Contact

**LinkedIn:** [linkedin.com/in/tu-perfil](https://linkedin.com/in/tu-perfil)  
**Email:** landeriglesiasaldecoa@gmail.com