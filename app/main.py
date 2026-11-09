"""Shop-floor SOP copilot — FastAPI app.

Serves a mobile-first single-page UI and a small JSON API:
  GET  /                  the UI
  GET  /api/health        status (docs loaded, chunks, mode, key configured)
  GET  /api/documents     the SOPs, with revision + superseded flags
  POST /api/ask           {question} -> grounded answer + sources
  POST /api/escalate      {question} -> log it for a named human (no dead ends)
  GET  /api/unanswered    questions that were escalated and are awaiting a human

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000
The app reads GOOGLE_API_KEY from the environment for LLM answers and
embeddings. Without a key it still works: TF-IDF retrieval + extractive answers.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .rag import Index, answer_question, chunk_documents, load_documents

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DOCS_DIR = ROOT / "docs"
INDEX_PATH = BASE / "index.json"
QUERY_LOG = ROOT / "query_log.jsonl"
UNANSWERED_PATH = ROOT / "unanswered.json"

ESCALATE_TO = "Shift QC Supervisor / Safety Officer"

app = FastAPI(title="Shop-floor SOP Copilot")

# --- load documents + build retrieval index once at startup ---
_docs = load_documents(DOCS_DIR)
_chunks = chunk_documents(_docs)
_index = Index(_chunks)
_index.build_tfidf()  # always available (offline fallback)

API_KEY = os.environ.get("GOOGLE_API_KEY") or None
if API_KEY:
    if not _index.load_embeddings(INDEX_PATH):
        try:
            _index.build_embeddings(API_KEY)
            _index.save_embeddings(INDEX_PATH)
        except Exception:
            _index.embeddings = None  # retrieval falls back to TF-IDF


def _log_query(entry: dict) -> None:
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    with QUERY_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


class AskRequest(BaseModel):
    question: str


class EscalateRequest(BaseModel):
    question: str
    context: str = ""


@app.get("/")
def root():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "documents": len(_docs),
        "chunks": len(_chunks),
        "llm_configured": bool(API_KEY),
        "embeddings": _index.embeddings is not None,
        "mode": "llm" if API_KEY else "extractive (no API key)",
    }


@app.get("/api/documents")
def documents():
    out = []
    for d in _docs:
        rev = d["revision"]
        # newest revision per doc_id is current
        newest = max(x["revision"] for x in _docs if x["doc_id"] == d["doc_id"])
        out.append({
            "doc_id": d["doc_id"],
            "title": d["title"],
            "file": d["file"],
            "revision": rev,
            "effective_date": d["effective_date"],
            "superseded": rev < newest,
            "superseded_by": newest if rev < newest else "",
            "pages": len(d["pages"]),
        })
    return out


@app.post("/api/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        return {"answer": "Please type a question.", "found": False, "sources": []}
    result = answer_question(_index, question, API_KEY)
    _log_query({
        "question": question,
        "answer": result["answer"],
        "found": result["found"],
        "confidence": result["confidence"],
        "mode": result["mode"],
        "safety_critical": result["safety_critical"],
        "sources": [
            {"doc_id": s["doc_id"], "revision": s["revision"], "page": s["page"]}
            for s in result["sources"]
        ],
    })
    return result


@app.post("/api/escalate")
def escalate(req: EscalateRequest):
    """Log an unanswered question for a named human. No dead ends."""
    entry = {
        "question": req.question.strip(),
        "context": req.context.strip(),
        "routed_to": ESCALATE_TO,
        "status": "awaiting human",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    items = []
    if UNANSWERED_PATH.exists():
        items = json.loads(UNANSWERED_PATH.read_text() or "[]")
    items.append(entry)
    UNANSWERED_PATH.write_text(json.dumps(items, indent=2))
    _log_query({
        "question": entry["question"],
        "answer": f"Escalated to {ESCALATE_TO}",
        "found": False,
        "confidence": 0.0,
        "mode": "escalation",
        "safety_critical": False,
        "sources": [],
    })
    return {"logged": True, "routed_to": ESCALATE_TO}


@app.get("/api/unanswered")
def unanswered():
    if not UNANSWERED_PATH.exists():
        return []
    return json.loads(UNANSWERED_PATH.read_text() or "[]")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
