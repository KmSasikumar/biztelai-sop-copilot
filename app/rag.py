"""RAG engine for the shop-floor SOP copilot.

Pipeline: PDF text extraction (pypdf) -> chunking -> retrieval -> grounded answer.
Retrieval uses Gemini embeddings when a GOOGLE_API_KEY is available; otherwise it
falls back to a pure-Python TF-IDF index (no key, no network needed for retrieval).
Generation uses Gemini (gemini-2.5-flash) with a strict grounding prompt; without a
key the app answers extractively (returns the best retrieved passage verbatim).

Design notes (see THINKING.md for the reasoning):
- The newest revision of a document is the current one; older revisions of the same
  document are marked superseded and the answer must come from the current revision.
- If the retrieved passages do not contain the answer, the app says so and does not
  guess. An unanswered question is never a dead end (see the escalation endpoint).
- Safety-critical topics (lockout/tagout, stored energy, energised equipment) get a
  warning banner and a highlighted route to a human; the SOP is the authority, not
  this app.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
from pypdf import PdfReader

GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_BASE = f"https://{GEMINI_HOST}/v1beta"
EMBED_MODEL = "models/gemini-embedding-001"
GEN_MODEL = "gemini-2.5-flash"

# Questions about these topics are safety-critical: show the warning banner.
SAFETY_KEYWORDS = [
    "lockout", "lock out", "tagout", "tag out", "loto",
    "stored energy", "energised", "energized", "isolate the machine",
    "remove a lock", "remove the lock", "remove a lockout",
    "electrical cabinet", "release stored", "zero energy",
]

# Below this best-match score the app says it cannot find the answer.
EMBED_THRESHOLD = 0.30
TFIDF_THRESHOLD = 0.15

STOPWORDS = set(
    "a an the is are was were be been being what how who whom which when where why "
    "do does did can could should would will shall may might i you he she it we they "
    "my your his her its our their this that these those and or but if then so as at "
    "by for with to of in on from into about over under per please tell me give show "
    "the".split()
)


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


# ---------------------------------------------------------------------------
# Document loading + chunking
# ---------------------------------------------------------------------------

def _parse_revision(text: str) -> str:
    m = re.search(r"Revision\s+0*(\d+)", text[:1500])
    return f"Rev {m.group(1)}" if m else "Rev ?"


def _parse_effective_date(text: str) -> str:
    m = re.search(r"Effective Date\s+(\d{2}-[A-Za-z]{3}-\d{4})", text[:1500])
    return m.group(1) if m else ""


# Lines that are document furniture (headers/footers), not content. pypdf
# extracts the title block as label and value on SEPARATE lines, so both the
# label lines ("Document No.") and their value lines ("MNT-MAN-CNC-02",
# "02", "20-Jan-2026", "S. Arun, Maintenance Engineer") must be stripped —
# otherwise they form junk chunks that out-rank the passages that actually
# answer a question.
_FURNITURE = [
    re.compile(r"Kaveri Precision Components"),
    re.compile(r"Uncontrolled copy when printed"),
    re.compile(r"^\s*Page\s+\d+\s*$"),
    re.compile(r"^\s*Page\s*$"),
    re.compile(r"^\s*Document No\.?\s*$"),
    re.compile(r"^\s*Revision\s*$"),
    re.compile(r"^\s*Effective Date\s*$"),
    re.compile(r"^\s*Prepared By\s*$"),
    re.compile(r"^\s*Approved By\s*$"),
    re.compile(r"^\s*See footer\s*$"),
    re.compile(r"^(SAF-SOP|QC-SOP|MNT-MAN)-[A-Z0-9-]+\s*$"),
    re.compile(r"^\s*0\d\s*$"),                       # revision number alone
    re.compile(r"^\s*\d{2}-[A-Za-z]{3}-\d{4}\s*$"),   # date alone
    re.compile(r"^\s*[A-Z]\.\s+[A-Z][a-z]+,\s+[A-Z]"),  # "S. Arun, Maintenance Engineer"
]


def _clean_page(text: str, title: str = "") -> str:
    lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if title and s == title:
            continue
        if any(p.search(ln) for p in _FURNITURE):
            continue
        lines.append(ln)
    return "\n".join(lines)


def load_documents(docs_dir: Path) -> list[dict]:
    """Extract text from every SOP pdf in docs_dir (Sample_Questions.pdf excluded)."""
    docs = []
    for pdf in sorted(docs_dir.glob("*.pdf")):
        if pdf.name.lower().startswith("sample_questions"):
            continue
        reader = PdfReader(str(pdf))
        title = " ".join(pdf.stem.replace("_", " ").split())
        raw_pages = [(i + 1, page.extract_text() or "")
                     for i, page in enumerate(reader.pages)]
        # Parse revision/date from the RAW text (the title block is stripped
        # from the chunk text below, so it must be read before cleaning).
        full_raw = "\n".join(t for _, t in raw_pages)
        pages = [(n, _clean_page(t, title)) for n, t in raw_pages]
        doc_id = pdf.stem.split("_")[0]  # e.g. SAF-SOP-003
        docs.append({
            "doc_id": doc_id,
            "file": pdf.name,
            "title": title,
            "revision": _parse_revision(full_raw),
            "effective_date": _parse_effective_date(full_raw),
            "pages": pages,
        })
    return docs


def chunk_documents(docs: list[dict], chunk_chars: int = 700, overlap: int = 120) -> list[dict]:
    """Split each document into overlapping chunks, keeping doc/page metadata.

    The newest revision of a document is current; older revisions of the same
    doc_id are marked superseded (their chunks are still indexed, but the answer
    must come from the current revision).
    """
    # newest revision per doc_id is current
    newest: dict[str, str] = {}
    for d in docs:
        rev = d["revision"]
        if d["doc_id"] not in newest or rev > newest[d["doc_id"]]:
            newest[d["doc_id"]] = rev

    chunks: list[dict] = []
    for d in docs:
        superseded = d["revision"] < newest[d["doc_id"]]
        # join pages with a page marker so chunks keep their page number
        segments: list[tuple[int, str]] = []
        for page_no, text in d["pages"]:
            segments.append((page_no, text))
        # build one text with page markers, then chunk on paragraph boundaries
        buf = ""
        buf_page = 1
        for page_no, text in segments:
            for para in text.split("\n"):
                para = para.strip()
                if not para:
                    continue
                if len(buf) + len(para) + 1 > chunk_chars and buf:
                    chunks.append({
                        "text": buf.strip(),
                        "doc_id": d["doc_id"],
                        "file": d["file"],
                        "title": d["title"],
                        "revision": d["revision"],
                        "effective_date": d["effective_date"],
                        "page": buf_page,
                        "superseded": superseded,
                        "superseded_by": newest[d["doc_id"]] if superseded else "",
                    })
                    # overlap: keep the last ~overlap chars as the start of next chunk
                    buf = buf[-overlap:] + " " + para
                    buf_page = page_no
                else:
                    buf = (buf + " " + para).strip()
                    buf_page = page_no
        if buf.strip():
            chunks.append({
                "text": buf.strip(),
                "doc_id": d["doc_id"],
                "file": d["file"],
                "title": d["title"],
                "revision": d["revision"],
                "effective_date": d["effective_date"],
                "page": buf_page,
                "superseded": superseded,
                "superseded_by": newest[d["doc_id"]] if superseded else "",
            })
    return chunks


# ---------------------------------------------------------------------------
# Gemini API (stdlib only — no extra dependency)
# ---------------------------------------------------------------------------

def _gemini_post(api_key: str, path: str, body: dict) -> dict:
    """POST to the Gemini API, retrying transient rate-limit/server errors."""
    import time
    import urllib.error

    last_error: Exception | None = None
    for attempt, delay in enumerate((0, 2, 5)):
        if attempt:
            time.sleep(delay)
        req = urllib.request.Request(
            GEMINI_BASE + path,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (429, 500, 502, 503) and attempt < 2:
                print(f"Gemini {e.code} on {path}; retrying in {delay or 2}s…",
                      file=sys.stderr)
                continue
            raise
        except Exception as e:  # network errors: retry once
            last_error = e
            if attempt < 2:
                continue
            raise
    raise last_error  # pragma: no cover


def embed_texts(api_key: str, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts with gemini-embedding-001 (one call per text)."""
    vectors = []
    for t in texts:
        result = _gemini_post(api_key, f"/{EMBED_MODEL}:embedContent", {
            "model": EMBED_MODEL,
            "content": {"parts": [{"text": t[:8000]}]},
        })
        vectors.append(result["embedding"]["values"])
    return vectors


def generate_text(api_key: str, prompt: str) -> str:
    result = _gemini_post(api_key, f"/models/{GEN_MODEL}:generateContent", {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1},
    })
    candidates = result.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


# ---------------------------------------------------------------------------
# Retrieval: embeddings (preferred) or TF-IDF (offline fallback)
# ---------------------------------------------------------------------------

class Index:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.embeddings: np.ndarray | None = None
        self.tfidf_vocab: list[str] = []
        self.tfidf_matrix: np.ndarray | None = None
        self.tfidf_idf: np.ndarray | None = None

    # -- embeddings --
    def build_embeddings(self, api_key: str) -> None:
        texts = [f"{c['title']} {c['revision']}. {c['text']}" for c in self.chunks]
        vectors = embed_texts(api_key, texts)
        arr = np.array(vectors, dtype=np.float64)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        self.embeddings = arr / np.maximum(norms, 1e-9)

    def save_embeddings(self, path: Path) -> None:
        path.write_text(json.dumps({"vectors": self.embeddings.tolist()}))

    def load_embeddings(self, path: Path) -> bool:
        if not path.exists():
            return False
        data = json.loads(path.read_text())
        arr = np.array(data["vectors"], dtype=np.float64)
        if arr.shape[0] != len(self.chunks):
            return False
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        self.embeddings = arr / np.maximum(norms, 1e-9)
        return True

    # -- TF-IDF fallback --
    def build_tfidf(self) -> None:
        docs_tokens = [tokenize(c["text"] + " " + c["title"]) for c in self.chunks]
        vocab = sorted({w for toks in docs_tokens for w in toks})
        idx = {w: i for i, w in enumerate(vocab)}
        n = len(docs_tokens)
        df = np.zeros(len(vocab))
        for toks in docs_tokens:
            for w in set(toks):
                df[idx[w]] += 1
        idf = np.log((n + 1) / (df + 1)) + 1.0
        mat = np.zeros((n, len(vocab)))
        for r, toks in enumerate(docs_tokens):
            for w in toks:
                mat[r, idx[w]] += 1.0
            mat[r] = mat[r] * idf
            norm = np.linalg.norm(mat[r])
            if norm > 0:
                mat[r] /= norm
        self.tfidf_vocab = vocab
        self.tfidf_matrix = mat
        self.tfidf_idf = idf

    def _scores_embed(self, query: str, api_key: str) -> np.ndarray:
        q = np.array(embed_texts(api_key, [query])[0], dtype=np.float64)
        q = q / max(np.linalg.norm(q), 1e-9)
        return self.embeddings @ q

    def _scores_tfidf(self, query: str) -> np.ndarray:
        idx = {w: i for i, w in enumerate(self.tfidf_vocab)}
        vec = np.zeros(len(self.tfidf_vocab))
        for w in tokenize(query):
            if w in idx:
                vec[idx[w]] += 1.0
        vec = vec * self.tfidf_idf
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        scores = self.tfidf_matrix @ vec
        # Phrase bonus: a chunk that contains a multi-word phrase from the
        # question (e.g. "coolant concentration", "lockout tagout") is far more
        # likely to be the answer than one matching only generic single words.
        toks = tokenize(query)
        if len(toks) >= 2:
            chunk_texts = [c["text"].lower() for c in self.chunks]
            for a, b in zip(toks, toks[1:]):
                phrase = f"{a} {b}"
                for i, ct in enumerate(chunk_texts):
                    if phrase in ct:
                        scores[i] += 0.15
        return scores

    def retrieve(self, query: str, api_key: str | None, top_k: int = 4):
        """Return (ranked [(chunk, score)], threshold, mode).

        Top-k by relevance, plus supersession context: when a retrieved chunk
        belongs to a document that has a superseded revision, the best-scoring
        chunk from that superseded revision is appended (if relevant enough).
        This lets the answer explain that an old rule was replaced, instead of
        silently ignoring the old revision or, worse, quoting it as current.
        """
        if api_key and self.embeddings is not None:
            scores = self._scores_embed(query, api_key)
            threshold, mode = EMBED_THRESHOLD, "embeddings"
            sup_threshold = 0.50
        else:
            scores = self._scores_tfidf(query)
            threshold, mode = TFIDF_THRESHOLD, "tfidf"
            sup_threshold = 0.05
        order = np.argsort(-scores)
        ranked = [(int(i), float(scores[i])) for i in order[:top_k]]
        picked = {i for i, _ in ranked}
        # Supersession context: best superseded chunk per doc_id in the top-k.
        for i, _ in list(ranked):
            doc_id = self.chunks[i]["doc_id"]
            best_sup, best_score = None, sup_threshold
            for j, c in enumerate(self.chunks):
                if j in picked or c["doc_id"] != doc_id or not c["superseded"]:
                    continue
                if scores[j] > best_score:
                    best_sup, best_score = j, float(scores[j])
            if best_sup is not None:
                ranked.append((best_sup, best_score))
                picked.add(best_sup)
        return [(self.chunks[i], s) for i, s in ranked], threshold, mode


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------

NOT_FOUND = "I couldn't find this in the provided documents."

ANSWER_PROMPT = """You are a shop-floor SOP copilot for a manufacturing plant. Answer the supervisor's question using ONLY the passages below, which come from the plant's SOPs and manuals. If the passages do not contain the answer, reply with exactly this sentence and nothing else: "I couldn't find this in the provided documents."

Rules:
- Give the direct answer first: the value with its unit, the rule, or the step — then stop. Do not lecture and do not add information that is not in the passages.
- For a procedure, list the steps in order, IN FULL. Never compress a safety step into a summary.
- If a passage is marked SUPERSEDED, it is an old revision. Answer from the current revision and say the older revision is superseded by it.
- If the question describes a rule that appears ONLY in a SUPERSEDED passage (the old revision), do NOT say "not found". Explain that that rule was in the old revision, it was superseded by the current revision, and give the current revision's rule instead.
- If the question is ambiguous, say which interpretation you used in one short clause.
- Keep the answer short enough to read on a phone while standing on the shop floor.

Passages:
{passages}

Question: {question}

Answer:"""


def is_safety_critical(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in SAFETY_KEYWORDS)


def answer_question(index: Index, question: str, api_key: str | None) -> dict:
    """Answer one question. Never guesses: returns found=False when the docs lack it."""
    ranked, threshold, mode = index.retrieve(question, api_key, top_k=4)
    best_score = ranked[0][1] if ranked else 0.0
    safety = is_safety_critical(question)

    sources = []
    for chunk, score in ranked:
        sources.append({
            "doc_id": chunk["doc_id"],
            "file": chunk["file"],
            "title": chunk["title"],
            "revision": chunk["revision"],
            "effective_date": chunk["effective_date"],
            "page": chunk["page"],
            "superseded": chunk["superseded"],
            "superseded_by": chunk["superseded_by"],
            "excerpt": chunk["text"][:500],
            "score": round(score, 3),
        })

    if best_score < threshold:
        return {
            "answer": NOT_FOUND,
            "found": False,
            "confidence": round(best_score, 3),
            "mode": mode,
            "safety_critical": safety,
            "sources": sources,
        }

    if api_key:
        passages = ""
        for chunk, score in ranked:
            tag = " [SUPERSEDED — old revision]" if chunk["superseded"] else ""
            passages += (
                f"\n--- {chunk['doc_id']} {chunk['revision']} (page {chunk['page']}){tag} ---\n"
                f"{chunk['text']}\n"
            )
        prompt = ANSWER_PROMPT.format(passages=passages, question=question)
        try:
            text = generate_text(api_key, prompt)
        except Exception as e:
            print(f"LLM call failed ({type(e).__name__}: {e}); using fallback.",
                  file=sys.stderr)
            text = ""
        if not text:
            # LLM call failed. Only fall back to the retrieved passages when the
            # match is strong — otherwise an irrelevant passage would be served
            # as if it were the answer (worse than saying "not found"). Return
            # the top two passages: the best match is not always the one that
            # holds the answer (e.g. a dimensions table can rank just below the
            # procedure text), and the UI labels this as extractive mode.
            if best_score >= 0.60:
                top_texts = [c["text"] for c, _ in ranked[:2]]
                return {
                    "answer": "\n\n---\n\n".join(top_texts),
                    "found": True,
                    "confidence": round(best_score, 3),
                    "mode": mode + "+extractive-fallback",
                    "safety_critical": safety,
                    "sources": sources,
                }
            return {
                "answer": NOT_FOUND,
                "found": False,
                "confidence": round(best_score, 3),
                "mode": mode + "+llm-unavailable",
                "safety_critical": safety,
                "sources": sources,
            }
        # The model may still say it cannot find it — honour that.
        found = NOT_FOUND not in text
        return {
            "answer": text,
            "found": found,
            "confidence": round(best_score, 3),
            "mode": mode + "+llm",
            "safety_critical": safety,
            "sources": sources,
        }

    # No API key: extractive mode — return the best passage verbatim.
    return {
        "answer": ranked[0][0]["text"],
        "found": True,
        "confidence": round(best_score, 3),
        "mode": mode + "+extractive",
        "safety_critical": safety,
        "sources": sources,
    }
