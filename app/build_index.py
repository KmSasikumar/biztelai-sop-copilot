"""Pre-build the embeddings index and save it to app/index.json.

Run once (with GOOGLE_API_KEY set) so the app starts fast and does not need to
embed all chunks on every start. The app still embeds each *question* at query
time, so a key is needed for embedding retrieval; without a key the app uses
the TF-IDF fallback instead.

Usage:  GOOGLE_API_KEY=... python -m app.build_index
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag import Index, chunk_documents, load_documents  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
INDEX_PATH = ROOT / "app" / "index.json"


def main() -> int:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY is not set. Cannot build the embeddings index.")
        return 2
    docs = load_documents(DOCS_DIR)
    chunks = chunk_documents(docs)
    print(f"{len(docs)} documents, {len(chunks)} chunks")
    index = Index(chunks)
    print("Embedding chunks (one API call per chunk)…")
    index.build_embeddings(api_key)
    index.save_embeddings(INDEX_PATH)
    print(f"Saved {INDEX_PATH} ({INDEX_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
