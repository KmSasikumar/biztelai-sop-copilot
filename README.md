# Shop-floor SOP Copilot

A simple working app (FastAPI + a mobile-friendly UI + RAG over the provided SOP PDFs) that
lets a manufacturing shift supervisor ask a question in plain words and get a short, grounded
answer — with the source document and revision shown. If the answer is not in the documents, the
app says so and does not guess.

Built by Sasi Kumar Yadav for the BiztelAI Technologies assignment (Junior Software Engineer,
Full Stack/AI). See [THINKING.md](THINKING.md) for the user research, the user journey, the AI
challenge, the improvement I added, and the final reflection.

## What it does

- **Ask a question** — type it in plain words ("AL-104 what do I do", "how many samples for
  600 housings"). The app retrieves the relevant SOP passages and answers from them.
- **Source shown, always** — every answer lists the source document, revision, page and the exact
  passage. QC-SOP-014 Rev03 is marked **SUPERSEDED by Rev04** wherever it appears, and answers
  come from the current revision.
- **Honest "I don't know"** — if the documents do not contain the answer, the app says
  "I couldn't find this in the provided documents." It never invents an answer.
- **Safety-critical guardrail** — questions about lockout/tagout, stored energy or energised
  equipment show a warning banner ("verify with the Safety Officer / an authorised person before
  acting — the SOP is the authority, not this app") and a highlighted route to a human.
- **No dead ends (the improvement)** — when the copilot cannot answer, one tap logs the exact
  question and routes it to the Shift QC Supervisor / Safety Officer, so the question is not lost
  and a human answers it. Every question and answer is also written to an audit log
  (`query_log.jsonl`), so the plant can see what the copilot was asked and where the documents
  are thin.
- **Works without an API key** — with a Gemini API key you get embedding retrieval + LLM
  answers; without one, the app falls back to TF-IDF retrieval and returns the most relevant
  passage(s) verbatim (extractive mode, clearly labelled in the UI). If the LLM API is
  temporarily unreachable, it falls back to the top two retrieved passages instead of failing
  or guessing — and only when the match is strong; otherwise it says "not found".

## Documents in this copilot

From the assignment's sample set (fictional plant: Kaveri Precision Components Pvt. Ltd., Hosur):

| Document | Revision | Effective | Status |
|---|---|---|---|
| SAF-SOP-003 — Lockout / Tagout Procedure | Rev 05 | 12-Feb-2026 | Current |
| QC-SOP-014 — Incoming Material Inspection | Rev 04 | 01-Jul-2026 | **Current** (supersedes Rev 03) |
| QC-SOP-014 — Incoming Material Inspection | Rev 03 | 15-Mar-2023 | **Superseded by Rev 04** |
| MNT-MAN-CNC-02 — TX-200 Preventive Maintenance Manual | Rev 02 | 20-Jan-2026 | Current |

Rev04 changed the sampling plan (lot-size based instead of a fixed 5 samples), made the Material
Test Certificate mandatory, moved quarantine to Cage Q1, switched to digital form QF-07A, and added
the BH-220 critical dimensions. The app answers from Rev04 and says so when a question touches
something Rev03 used to say differently.

## How to run it

### Requirements

- Python 3.10+
- A Google Gemini API key (free from [Google AI Studio](https://aistudio.google.com/app/apikey))
  — optional but recommended; without it the app runs in extractive mode (see above).

### On macOS / Linux

```bash
# 1. Get a free Gemini API key from https://aistudio.google.com/app/apikey
export GOOGLE_API_KEY=your_key_here        # optional — the app works without it

# 2. Start the app (creates a virtual environment and installs dependencies)
./run.sh
```

### On Windows (PowerShell)

```powershell
$env:GOOGLE_API_KEY = "your_key_here"      # optional — the app works without it
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Open it from your phone (same Wi-Fi)

1. Find your laptop's Wi-Fi address. The `run.sh` script prints it, or:
   - macOS: `ipconfig getifaddr en0`
   - Windows: `ipconfig` (look for "IPv4 Address" under your Wi-Fi adapter)
   - Linux: `hostname -I`
2. On your phone (same Wi-Fi), open `http://<your-laptop-IP>:8000` — for example,
   `http://192.168.1.5:8000`.
3. The UI is mobile-first (large text, big tap targets, sample questions as tappable chips).

### API

- `GET /` — the UI
- `GET /api/health` — status (documents, chunks, whether the LLM is configured)
- `GET /api/documents` — the SOPs with revision and superseded flags
- `POST /api/ask` — `{"question": "..."}` → answer + sources + confidence + safety flag
- `POST /api/escalate` — `{"question": "..."}` → logs the question for the Shift QC
  Supervisor / Safety Officer
- `GET /api/unanswered` — questions that were escalated and are awaiting a human

## How it works (RAG)

1. **Load** — the 4 SOP PDFs are read with `pypdf` (the sample-questions PDF is not indexed).
2. **Chunk** — each document is split into overlapping chunks (~700 chars), keeping the document,
   revision, page and a "superseded" flag (the newest revision of a document is current; older
   revisions are superseded).
3. **Retrieve** — the question is embedded with Gemini (`gemini-embedding-001`) and matched
   against a pre-built embedding index (`app/index.json`, 3072-dim vectors, cosine similarity);
   without an API key, a pure-Python TF-IDF index is used instead. The top passages are returned,
   plus the best superseded-revision passage when one is relevant (so the answer can explain that
   an old rule was replaced).
4. **Generate** — Gemini (`gemini-2.5-flash`, temperature 0.1) answers using ONLY the retrieved
   passages, under a strict prompt: give the direct answer first; list procedure steps in full,
   never compressed; prefer the current revision and say when an older one is superseded; state
   which interpretation was used if the question is ambiguous; if the passages do not contain the
   answer, reply exactly "I couldn't find this in the provided documents." If the best retrieval
   score is below a threshold, the app answers "not found" without calling the LLM. If the LLM
   call fails, it falls back to the retrieved passage (only when the match is strong) or to
   "not found".
5. **Log** — every question, answer, sources and confidence are appended to `query_log.jsonl`.

## My own 5 questions (and the app's answers)

I wrote these to test the app beyond the sample questions. The answers below are what the app
actually returned (LLM mode, Gemini; sources in brackets).

**1. A lot of 600 BH-220 housings arrived. How many samples do I inspect, and how many minor defects can I accept?**

> Inspect 32 samples, and accept if minor defects are 1 or fewer.
> [QC-SOP-014 Rev04, §4 Sampling Plan — lot size 501–3,200 → 32 samples, accept 1 or fewer minor defects, reject 2 or more.]

**2. The supplier forgot the Material Test Certificate. Can I still inspect the lot?**

> No, the lot is put on HOLD and must not be inspected or accepted until the MTC is received.
> [QC-SOP-014 Rev04, §5 step 2 — the MTC is mandatory. Rev03 did not require an MTC; Rev04 supersedes it.]

**3. What is the chuck clamping pressure range for the TX-200?**

> 2.0 – 2.5 MPa
> [MNT-MAN-CNC-02 Rev02, §3 Normal Operating Parameters.]

**4. How do I replace a hydraulic hose on the TX-200?**

> 1. Isolate the machine as per SAF-SOP-003, including releasing stored hydraulic pressure.
> 2. Confirm the panel pressure gauge reads zero before loosening any fitting.
> 3. Place a drip tray under the hose and loosen the fittings slowly.
> 4. Fit a new hose of the same rating and tighten fittings.
> 5. Remove locks as per SAF-SOP-003, start the hydraulic unit and confirm pressure returns to 3.5 – 4.0 MPa with no leaks.
> [MNT-MAN-CNC-02 Rev02, §7 Replacing a Hydraulic Hose. The app also shows the safety-critical warning for this question, because it involves isolation and stored hydraulic pressure.]

**5. What is the overtime rate for a maintenance technician working a Sunday shift?**

> I couldn't find this in the provided documents.
> [This is the question the documents cannot answer — there is no pay, HR or overtime information in any of the SOPs. The app refused instead of guessing, and offered to send the question to a supervisor.]

## Sample questions (tested)

All 5 sample questions return correct, sourced answers:

| # | Question | App's answer | Source |
|---|---|---|---|
| 1 | Recommended coolant concentration for the TX-200? | 6 – 8 % | MNT-MAN-CNC-02 Rev02, §3 |
| 2 | Alarm AL-104 — meaning and operator action? | Way lube oil level low. Top up with ISO VG 68 oil to the MAX mark, then press RESET. Machine can continue after reset. | MNT-MAN-CNC-02 Rev02, §6 |
| 3 | Who is allowed to remove a lockout lock? | Each authorised person removes only their own lock. Nobody may remove another person's lock. If the owner is absent, the Production Manager and the Safety Officer must both authorise removal. | SAF-SOP-003 Rev05, §5–§6 (safety-critical banner shown) |
| 4 | Outer diameter tolerance for the BH-220 bearing housing? | ± 0.050 mm (nominal 90.000 mm) | QC-SOP-014 Rev04, §6 |
| 5 | How often should spindle runout be checked, and who does it? | Monthly, by the Maintenance technician. | MNT-MAN-CNC-02 Rev02, §4 |

## Project layout

```
.
├── app/
│   ├── main.py          # FastAPI app + API endpoints
│   ├── rag.py           # PDF loading, chunking, retrieval, grounded answering
│   ├── build_index.py   # Pre-build the embeddings index (needs GOOGLE_API_KEY)
│   ├── index.json       # Pre-built embedding vectors (21 chunks, 3072-dim)
│   └── static/index.html# Mobile-first UI
├── docs/                # The 4 sample SOP PDFs (+ Sample_Questions.pdf)
├── requirements.txt
├── run.sh               # One-command start (macOS/Linux)
├── README.md
└── THINKING.md          # User research, journey, AI challenge, improvement, reflection
```

Runtime files created by the app (git-ignored): `query_log.jsonl` (audit log of every
question/answer) and `unanswered.json` (questions escalated to a human).

## Notes and limits

- The app answers only from these 4 sample SOPs. It will not answer HR, pay, or general-knowledge
  questions — it says so instead of guessing.
- The Gemini API key is read from the `GOOGLE_API_KEY` environment variable and is never stored
  in the repo. Do not commit a key.
- The free Gemini API tier rate-limits requests; the app retries transient 429/5xx errors a few
  times and then falls back gracefully (passage, or "not found").
- The plant, documents and procedures are fictional samples provided for this assignment.
