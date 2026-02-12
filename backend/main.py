from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from .agent import respond
from .config import settings
from .metrics import snapshot
from .rag import ingest_markdown
from .schemas import ChatIn
from .store import close_handoff, list_handoffs
from .tools import _cfg, validate_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        n = ingest_markdown()
        print(f"[RAG] Ingeridas {n} secciones")
    except Exception as e:
        print("[RAG] fallo de ingesta:", e)

    try:
        errs = validate_config()
        if errs:
            print("[CONFIG] Errores de configuración:")
            for e in errs:
                print(" -", e)
        else:
            print("[CONFIG] clinic_config.yaml OK")
    except Exception as e:
        print("[CONFIG] fallo validando config:", e)

    yield


app = FastAPI(title="Dental Agent", lifespan=lifespan)


@app.post("/chat")
def chat(inp: ChatIn):
    print("DEBUG ChatIn:", inp.model_dump())
    reply, sources = respond(inp.user, sender=inp.sender)
    print("DEBUG respond:", reply, sources, type(sources))
    return {"reply": reply, "sources": sources}


@app.post("/admin/reload-config")
def reload_config():
    # invalidar caché leyendo una vez
    from importlib import reload

    import backend.tools as tools

    reload(tools)
    return {"ok": True}


def _validate_twilio(request: Request, form: dict) -> bool:
    """
    Valida que el POST viene de Twilio.
    - Requiere settings.TWILIO_AUTH_TOKEN
    - Usa el header X-Twilio-Signature
    """
    sig = request.headers.get("X-Twilio-Signature", "")
    if not sig or not getattr(settings, "TWILIO_AUTH_TOKEN", None):
        return False

    # Twilio valida contra la URL pública exacta (incluyendo https y path)
    url = str(request.url)
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, form, sig)


@app.post("/whatsapp-twilio")
async def whatsapp_twilio(request: Request, Body: str = Form(""), From: str = Form("")):
    # Ojo: el validador necesita el form completo tal cual
    form = dict(await request.form())

    # Firma Twilio: si falla, corta (evita basura/ataques)
    if not _validate_twilio(request, form):
        # Respuesta vacía 403 (Twilio lo verá como fallo, bien)
        return Response("Forbidden", status_code=403)

    text = (Body or "").strip()
    sender = (From or "").strip()

    # No inventes "hola" aquí. Si viene vacío, responde algo neutro.
    if not text:
        text = "Hola"

    reply, sources = respond(text, sender=sender)

    twiml = MessagingResponse()
    twiml.message(reply)

    return Response(str(twiml), media_type="application/xml")


@app.get("/admin/metrics")
def metrics():
    return snapshot()


@app.get("/", include_in_schema=False)
def root():
    return HTMLResponse('<h3>Dental Agent</h3><p><a href="/docs">/docs</a></p>')


@app.get("/admin/handoffs")
def admin_handoffs(status: str = "open", limit: int = 20):
    return {"handoffs": list_handoffs(limit=limit, status=status)}


@app.post("/admin/handoffs/{handoff_id}/close")
def admin_close_handoff(handoff_id: int):
    ok = close_handoff(handoff_id)
    return {"ok": ok, "id": handoff_id}


@app.post("/admin/reindex")
def reindex():
    md_path = Path(__file__).resolve().parent / "data" / "dental_faq.md"
    n = ingest_markdown(str(md_path))
    return {"ok": True, "chunks": n, "source": str(md_path)}


@app.get("/admin/config")
def show_config():
    c = _cfg().copy()
    c["address"] = c.get("address", "")
    return {"address": c.get("address"), "map_url": c.get("map_url")}
