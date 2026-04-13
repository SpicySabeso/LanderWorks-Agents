"""
API del RAG PDF Agent v2.

Endpoints:
  POST /rag-agent/upload              → sube y procesa un PDF
  POST /rag-agent/chat                → pregunta con historial
  POST /rag-agent/compare             → pregunta sobre dos PDFs a la vez
  GET  /rag-agent/session/{id}        → info de sesión
  DELETE /rag-agent/session/{id}      → elimina sesión
  GET  /rag-agent/demo                → página demo con UI
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .demo_template import demo_html
from .rag_engine import (
    cleanup_session,
    create_session_id,
    get_answer,
    get_answer_compare,
    process_pdf,
    session_exists,
)

router = APIRouter(prefix="/rag-agent", tags=["rag-agent"])

UPLOAD_DIR = Path(__file__).resolve().parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024


# ── Schemas ───────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    session_id: str
    question: str
    chat_history: list[dict] = []


class CompareRequest(BaseModel):
    session_id_a: str
    session_id_b: str
    question: str
    chat_history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    session_id: str


class CompareResponse(BaseModel):
    answer: str
    sources_a: list[dict]
    sources_b: list[dict]


class UploadResponse(BaseModel):
    session_id: str
    pages: int
    chunks: int
    filename: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Sube y procesa un PDF, devuelve session_id."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    content = await file.read()
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera el límite de 20 MB.")

    session_id = create_session_id()
    pdf_path = UPLOAD_DIR / f"{session_id}.pdf"
    pdf_path.write_bytes(content)

    try:
        result = process_pdf(str(pdf_path), session_id)
        return UploadResponse(
            session_id=session_id,
            pages=result["pages"],
            chunks=result["chunks"],
            filename=file.filename,
            message=f"PDF procesado: {result['pages']} páginas, {result['chunks']} fragmentos indexados.",
        )
    except Exception as e:
        cleanup_session(session_id)
        raise HTTPException(status_code=500, detail=f"Error procesando el PDF: {str(e)}") from e
    finally:
        if pdf_path.exists():
            pdf_path.unlink()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """Pregunta sobre un PDF con historial de conversación."""
    if not payload.session_id or not payload.question.strip():
        raise HTTPException(status_code=400, detail="session_id y question son obligatorios.")

    if not session_exists(payload.session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada. Sube un PDF primero.")

    try:
        result = get_answer(
            question=payload.question,
            session_id=payload.session_id,
            chat_history=payload.chat_history,
        )
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            session_id=payload.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando respuesta: {str(e)}") from e


@router.post("/compare", response_model=CompareResponse)
def compare(payload: CompareRequest):
    """Pregunta sobre dos PDFs simultáneamente y compara sus contenidos."""
    if not payload.session_id_a or not payload.session_id_b:
        raise HTTPException(status_code=400, detail="session_id_a y session_id_b son obligatorios.")

    if not session_exists(payload.session_id_a):
        raise HTTPException(status_code=404, detail="Documento A no encontrado.")

    if not session_exists(payload.session_id_b):
        raise HTTPException(status_code=404, detail="Documento B no encontrado.")

    try:
        result = get_answer_compare(
            question=payload.question,
            session_id_a=payload.session_id_a,
            session_id_b=payload.session_id_b,
            chat_history=payload.chat_history,
        )
        return CompareResponse(
            answer=result["answer"],
            sources_a=result["sources_a"],
            sources_b=result["sources_b"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparando documentos: {str(e)}") from e


@router.get("/session/{session_id}")
def get_session_info(session_id: str):
    exists = session_exists(session_id)
    return {
        "session_id": session_id,
        "exists": exists,
        "message": "Sesión activa." if exists else "Sesión no encontrada.",
    }


@router.delete("/session/{session_id}")
def delete_session(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    cleanup_session(session_id)
    return {"ok": True, "message": f"Sesión {session_id} eliminada."}


@router.get("/demo", response_class=HTMLResponse)
def serve_demo():
    return HTMLResponse(content=demo_html())
