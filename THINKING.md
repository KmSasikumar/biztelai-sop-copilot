# THINKING.md — Shop-floor SOP Copilot (BiztelAI assignment)

**Candidate:** Sasi Kumar Yadav — B.Tech CSE (July 2026), Vellore Institute of Technology, CGPA 8.29/10.
Full-stack developer (Python, JavaScript, TypeScript, Java, React, Django, Node.js, FastAPI).
I have no manufacturing experience. Everything about the shop floor below is from the brief, the
sample documents, and research — and I have marked every assumption as one.

---

## Understand the user

### Who the supervisor is
A shift supervisor on the shop floor of a manufacturing plant (the sample documents are from a
fictional plant, Kaveri Precision Components, Hosur). They run a shift of operators — in the sample
docs, the shaft machining line with TX-200 CNC turning centres (CNC-04 to CNC-09) and the
incoming-material inspection area. They are the person everyone turns to when something is unclear:
an alarm on a machine, a delivery that arrived without its test certificate, a lock that needs removing,
a hose that needs replacing. They are responsible for keeping the line running *and* for keeping people
safe, which means they cannot afford to guess.

### What they are trying to do
Get a correct, trustworthy answer in under a minute, in the middle of a shift, usually while standing on
the shop floor — and then act on it. The questions are concrete and urgent: "What does alarm AL-104
mean and what do I do?", "How many samples do I inspect for this lot?", "Who is allowed to remove
this lock?" The answer has to be the *current* procedure, not an old revision, and it has to be short
enough to read on a phone screen.

### What frustrates them today
- **Hundreds of PDFs, no search.** SOPs, manuals and procedures live as PDF files (or printed
  binders). Finding the right paragraph means opening the right document and scanning it — while a
  machine is stopped.
- **Revisions are a trap.** The same procedure exists in more than one revision. The sample set has
  QC-SOP-014 in Rev03 *and* Rev04, and Rev04 changes the sampling plan, makes the Material Test
  Certificate mandatory, and moves quarantine to a different cage. Following the old revision is a real,
  quiet way to do the wrong thing.
- **The answer is often "ask someone and wait."** If the supervisor cannot find it, they call the QC
  manager, the maintenance engineer, or the safety officer — and wait. Meanwhile the line is stopped
  or the lot is sitting in the inspection area.
- **The phone is the device, but the documents are not phone-friendly.** PDFs are written for print:
  dense tables, small text, multi-page procedures. A supervisor with oily hands or gloves, in a noisy
  hall, does not want to pinch-zoom a PDF.
- **A wrong answer is worse than no answer.** If the copilot confidently gives the Rev03 sampling
  rule, or a torque value from the wrong machine, the supervisor may act on it. On a shop floor, a wrong
  maintenance or safety step can injure someone or scrap a whole lot. Trust is the whole product.

### Assumptions I am making (stated clearly)
1. The supervisor carries a phone or tablet on the floor and has Wi-Fi access to the plant network.
   (The brief says they use a phone or tablet; I assume plant Wi-Fi reaches the shop floor.)
2. The supervisor reads English. (All sample SOPs are in English; I assume the plant's working
   documents are in English.)
3. The supervisor is not a quality or maintenance specialist — they coordinate, they do not own the
   procedures. That is why they need the source shown: so they (or the specialist they call) can verify it.
4. The plant has a QMS app and a named Shift QC Supervisor / Safety Officer who can be reached
   when the copilot cannot answer. (The sample SOPs reference both roles.)
5. The supervisor's shift is time-pressured and interruption-driven: they will ask one question, get one
   answer, and move on. They will not read a long report.

---

## User journey

*(First draft — written by me, before asking any AI tool to critique it.)*

### The normal path
1. **Something happens on the floor.** The TX-200 shows alarm AL-104. Or a lot of BH-220 bearing
   housings arrives and the delivery note has no Material Test Certificate. Or a maintenance
   technician needs a lock removed and the person who put it on has left the plant.
2. **The supervisor opens the copilot on their phone.** One tap, no login, no searching through a
   file list. The app opens to a single search box.
3. **They type the question in plain words.** "AL-104 what do I do", "how many samples for 600
   housings", "who can remove a lockout lock". They do not need to know the document number or
   the exact SOP wording.
4. **The copilot answers in two or three sentences, and shows its source.** For example: "AL-104
   means the way lube oil level is low. Top up with ISO VG 68 oil to the MAX mark, then press RESET.
   The machine can continue after reset." Underneath: the source — MNT-MAN-CNC-02, Rev 02,
   Section 6 (Common Alarms). The supervisor can tap the source to see the exact passage.
5. **The supervisor acts, and the answer is short enough to re-read while doing it.** If the answer is
   a procedure (for example, replacing a hydraulic hose), the steps are numbered and in order.
6. **If the answer is not in the documents, the copilot says so plainly** — "I couldn't find this in the
   provided documents" — and does not guess. It offers one tap to send the question to the shift
   supervisor / safety officer, so the question is logged and a human answers it.

### What could go wrong
- **The copilot answers from the wrong revision.** The supervisor asks about incoming inspection
  and gets the Rev03 rule ("draw 5 samples from every lot") instead of the Rev04 lot-size sampling
  plan. They inspect the wrong number of samples and either reject a good lot or accept a bad one.
- **The copilot gives a confident, fluent answer that is not in any document.** The supervisor
  follows it because it sounds authoritative. On a safety procedure (lockout/tagout), that could injure
  someone.
- **The question is ambiguous and the copilot answers the wrong thing.** "What is the pressure?"
  could mean hydraulic pressure (3.5–4.0 MPa), chuck clamping pressure (2.0–2.5 MPa), or
  compressed air (5.5–6.5 bar). A single number with no label is dangerous.
- **The Wi-Fi drops on the shop floor.** The app will not load, or an answer takes 30 seconds to
  come back. The supervisor gives up and asks the nearest person instead — or guesses.
- **The answer is too long.** A five-paragraph answer on a phone screen, read in a noisy hall while a
  machine is stopped, gets skimmed — and the one critical step (for example, "confirm the pressure
  gauge reads zero before loosening any fitting") gets missed.
- **The supervisor trusts the app over the physical document or a senior colleague when they
  disagree.** The app is a helper, not the authority; the SOP itself is the authority. If the app and the
  printed SOP disagree, the supervisor needs to know the app might be out of date.
- **The supervisor is in a hurry and skips the source.** They read the answer, act, and never check
  which document it came from. If the answer was wrong, there is no trail back to the source.

---

## AI challenge

I asked Google Gemini (gemini-2.5-flash) to critique my user journey as a skeptical, experienced
plant manager and shop-floor supervisor. I asked it to attack my assumptions, the failure modes I
missed, whether a supervisor would actually trust the app, the "I don't know" behaviour, and safety /
liability. Below are the key parts of that conversation (lightly condensed; the full reply is in my
working notes), followed by my reflection.

### Key excerpts from the critique

**On my assumptions:**
> "Supervisor carries a phone on the floor with plant Wi-Fi. You live in a dream world, son. Phones:
> many areas are restricted for phones… a supervisor's hands are often greasy, gloved, or holding
> something… Plant Wi-Fi is often a joke. Spotty as hell, especially around massive metal machines…
> You think I'm going to trust a critical answer to a connection that drops every time someone starts
> a welder?"
>
> "Not a specialist (needs the source shown to verify). This is where you fundamentally misunderstand
> a supervisor. A supervisor *is* a specialist. They know their line inside and out. They're not looking
> for a textbook lesson; they're looking for a specific data point, a confirmation, or the one obscure
> procedure they don't do often. If they *have* to verify it by reading the SOP, why didn't they just
> read the SOP or ask a human in the first place?"

**On failure modes I missed:**
> "The SOPs themselves are flawed. Your AI is only as good as the garbage we feed it. What if the
> source SOP is outdated, incomplete, ambiguous, or just plain wrong?"
>
> "Supervisor misinterprets the *short answer*. '2-3 sentences' is a recipe for disaster. Nuance,
> caveats, context — these get lost. Procedures are often step-by-step for a reason."
>
> "Supervisor misinterprets their *own question*. If I ask 'What do I do about the lock?' and it's a
> LOTO lock, but I just meant a jammed padlock, your AI could lead me down a very dangerous path."
>
> "The 'one tap to human' fails or is too slow. What if the human is busy, in a meeting, off-site, or
> doesn't answer immediately? You've created a single point of failure."

**On trust:**
> "Absolutely not, not for anything critical. And if they use it once and it fails, it's dead to them.
> Humans provide context, judgment, and take responsibility… If an app tells me wrong, who do I
> yell at?"

**On "I don't know":**
> "Largely useless and potentially dangerous in a critical, time-pressured situation. 'I don't know' when
> a machine is alarming… doesn't help me *at all*. It just wastes precious time… You just added a
> useless step."

**On safety and liability:**
> "Wrong Answers = Catastrophe… If the app gives wrong steps for removing a lock, and that lock is
> a LOTO tag, someone could get seriously hurt or killed… Liability: who is on the hook? The
> supervisor who trusted it? The company that supplied the AI? Plant management for approving it?
> This needs to be crystal clear, in writing, *before* anything touches our floor."
>
> "How do we record *every single question asked* and *every single answer given* by the AI? If
> there's an incident, we need a full audit trail."

**Its top 3 objections:**
1. "Safety and Liability Are Unacceptable Risks."
2. "Lack of Trust and Real-World Practicality."
3. "'I Don't Know' Is Not an Option for Critical Issues."

**The one change it demanded before letting the app on its floor:**
> "The AI copilot *must be explicitly and verifiably restricted* from providing *any* direct, actionable
> instructions for safety-critical procedures (e.g. Lock Out Tag Out, emergency stops…). For any such
> query, its *only* allowed response is to immediately direct the supervisor to contact a specific, live
> human expert… providing that human's contact information and the *exact original question*, while
> stating 'THIS PROCEDURE REQUIRES IMMEDIATE HUMAN INTERVENTION. DO NOT PROCEED
> WITHOUT VERIFICATION FROM [HUMAN CONTACT].' The system must also log this interaction and
> alert the designated human expert directly and immediately."

### My reflection — what I agreed with, disagreed with, and changed

**Agreed — and changed the design:**
- **"I don't know" on its own is a dead end, not a feature.** The critique is right: telling a
  supervisor "I don't know" mid-shift and leaving them there wastes their time. I changed the design
  so that an unanswered question is never a dead end: the app logs the exact question, routes it to
  a named human role (Shift QC Supervisor / Safety Officer), and tells the supervisor plainly that it
  was logged and who will see it — plus "if this is urgent, call/radio them directly" (I do not pretend
  the log guarantees an instant reply). This became the ONE improvement (see below).
- **Every question and answer must be logged (audit trail).** I agreed completely. The app now
  writes every question, answer, sources, and confidence to a local query log (`query_log.jsonl`), so
  the plant can audit what the copilot said and spot where the documents are thin.
- **Short answers lose nuance — procedures must be shown in full.** I agreed. The app no longer
  compresses a procedure into 2–3 sentences. For procedures, it lists the steps in order, in full,
  from the retrieved passage. For a fact (a tolerance, a pressure, a count) it gives the direct value
  with its unit and source. The prompt now says: never summarise away a safety step.
- **The supervisor is a specialist, not a student.** I agreed. The app gives a direct, specific answer
  (the value, the step, the rule) — not a lesson. The source is shown so they can verify in seconds,
  not so they have to re-read the whole SOP. The value of the app is retrieval speed, not teaching.
- **Ambiguous questions are dangerous.** I agreed. When a question is ambiguous (for example,
  "lock" could mean a LOTO lock or a jammed padlock), the app states which interpretation it used
  and shows the source prominently, so a wrong interpretation is visible immediately instead of
  hidden inside a confident answer.
- **Wi-Fi / phone practicality is a real risk.** I agreed it is a risk I cannot fix. The mitigation I built
  in: the app runs on the local network (no internet needed for the app itself), and if the LLM API is
  unreachable it falls back to extractive mode — it returns the retrieved passage verbatim with its
  source — so retrieval still works offline. The UI is mobile-first (large text, big tap targets).

**Disagreed — and why:**
- **"Supervisors will never trust it, so it is useless."** Too absolute. The app is a retrieval aid, not
  a replacement for a human. For routine lookups (an alarm meaning, a tolerance, a sampling count)
  it is faster than finding the PDF, and it earns trust by showing sources and by saying "I don't
  know" honestly. For safety-critical actions, the guardrail and the escalation path apply. Trust is
  earned over time; it is not a reason to build nothing.
- **"If they have to verify by reading the SOP, why not just read the SOP?"** Because finding the
  right passage in seconds is the value. Verifying a cited passage takes seconds; finding it in a
  200-page manual takes minutes. The source is shown for verification, not as a requirement to
  re-read everything.
- **A blanket refusal to show safety procedures.** I disagreed with the demanded change as stated.
  Refusing to show the plant's own lockout procedure would make the app useless exactly when the
  supervisor needs the document most — and the SOP is the authority, not the app. Instead I
  implemented a guardrail: for safety-critical topics (lockout/tagout, stored energy, energised
  equipment) the answer is shown from the SOP **with a prominent warning banner** ("Safety-critical
  procedure — verify with the Safety Officer / an authorised person before acting. The SOP is the
  authority, not this app.") and the escalation to the Safety Officer is highlighted. I kept the
  procedure visible, but I made the app refuse to present itself as the authority for it. That is the
  honest middle ground, and I have written it down here so the decision is visible.
- **"One tap to a human fails if the human is busy."** Fair — and I do not pretend otherwise. The
  app logs the question so it is not lost, names who it was routed to, and tells the supervisor to call
  or radio them directly if it is urgent. A logged question with a named owner is better than an
  unlogged dead end, but it is not a guarantee of an instant reply, and the UI says so.

**What I changed in the app because of this critique:**
1. Safety-critical guardrail (warning banner + highlighted escalation) for LOTO / stored-energy /
   energised-equipment questions.
2. "No dead end" escalation: unanswered or low-confidence questions are logged and routed to a
   named human role, with honest wording about response time.
3. Full audit log of every question, answer, sources and confidence (`query_log.jsonl`).
4. Procedures shown as full numbered steps, never compressed into a summary.
5. Offline fallback: if the LLM API is unreachable, the app returns the retrieved passage verbatim
   with its source instead of failing.
6. The app states which interpretation it used when a question is ambiguous, and always shows the
   source document and revision so a wrong interpretation is visible.

---

## The improvement you added, and why you chose it

### The improvement: the copilot never leaves a supervisor without a next step

When the copilot cannot answer a question — or when its match is weak — it does not stop at
"I couldn't find this in the provided documents." It gives the supervisor an immediate next step:

1. **One tap to send the question to a named human.** A "Send this question to my supervisor"
   button appears on every unanswered question. It logs the exact question (with the time and the
   context that the copilot could not answer it from the SOPs) and routes it to the Shift QC
   Supervisor / Safety Officer. The app confirms what was logged and who will see it, and it is
   honest that the log does not guarantee an instant reply — "If this is urgent, call or radio them
   directly."
2. **A visible list of escalated questions.** A "Questions sent to a supervisor" section in the app
   shows every escalated question, who it was routed to, and whether it is still awaiting a human.
   So nothing disappears into a void.
3. **A full audit log.** Every question, answer, sources and confidence score is appended to
   `query_log.jsonl`. The plant can audit what the copilot said, and — just as importantly — can
   see which questions the copilot could *not* answer, which is the list of gaps in the documents.

On top of that, safety-critical questions (lockout/tagout, stored energy, energised equipment) get
a warning banner and a highlighted route to the Safety Officer, so the app never presents itself as
the authority for a safety procedure.

### Why I chose this one

It came directly from the user journey and the AI challenge. The journey showed the supervisor is
mid-shift, time-pressured, and stuck the moment the copilot cannot answer. The AI challenge (the
skeptical plant manager) attacked exactly that point: "'I don't know' when a machine is alarming…
doesn't help me *at all*. It just wastes precious time… You just added a useless step." He was
right. A copilot that says "I don't know" and stops is a dead end — and on a shop floor, a dead end
is not neutral, it costs production time and, if the supervisor then guesses, it can cost safety.

I considered two other improvements and did not choose them (they are in "what I'd build next"
below): a step-by-step checklist mode for procedures, and voice input for gloved hands. Both are
useful, but neither fixes the core failure the critique exposed — that the app abandons the user
at the worst moment. The escalation path fixes that. It also creates the feedback loop the critique
asked for: unanswered questions are logged, so the plant learns where its documents are thin, and
the audit log gives the accountability trail (who asked what, what the app answered, from which
source) that a safety investigation would need.

The improvement is deliberately small and honest: it does not promise an instant human reply (I
cannot guarantee one), it promises the question is logged, routed to a named role, and visible. That
is a claim I can keep.

---

## Final reflection

### What I would build next

1. **Voice input.** Supervisors often have gloved or oily hands. Tapping a question is workable,
   but speaking it would be faster and more realistic on the floor.
2. **A step-by-step checklist mode for procedures.** For multi-step work (lockout/tagout, replacing
   a hydraulic hose), show each step as a tappable checkbox so the supervisor can tick it off as
   they go and cannot accidentally skip a step. This was my second choice for the "one
   improvement" and is the natural next feature.
3. **Offline-first.** The app already runs on the local network, but the LLM call still needs
   internet. A small on-device model (or a cached extractive mode that is smarter about ranking)
   would keep the copilot usable when the plant's internet drops.
4. **A feedback loop on answers.** Let the supervisor mark an answer "helpful" or "wrong" in one
   tap, and feed that back into which passages get retrieved — and, more importantly, into a report
   for the people who own the SOPs, so the documents themselves improve.
5. **Role-aware routing.** Route quality questions to the SQE, safety questions to the Safety
   Officer, and maintenance questions to the Maintenance Manager, instead of one shared list.
6. **Revision-change alerts.** When a new SOP revision is added, the app should flag which answers
   changed, so supervisors are not caught by a silent update.

### What I am unsure about

- **Whether supervisors will actually use it instead of asking a human.** The critique was blunt
  about this, and it is the biggest open question. The app earns trust only by being right, showing
  its sources, and saying "I don't know" honestly — and trust, once lost by one wrong answer, is
  hard to win back. I do not know if that is enough.
- **Whether the plant Wi-Fi is reliable on the shop floor.** I assumed it reaches the floor. If it
  does not, the app is unreachable exactly when it is needed. The local-network deployment helps,
  but it does not fix a dead Wi-Fi zone.
- **Whether the SOPs themselves are complete and correct.** The copilot is only as good as the
  documents. If a procedure is outdated, ambiguous, or wrong, the app will faithfully retrieve the
  wrong thing. I built the revision handling (Rev04 over Rev03) for the sample set, but I do not
  know how the plant keeps its real SOPs current, or who owns that.
- **How the escalation works in practice.** I log the question and name a role, but I do not know
  who actually watches that list, or how fast they respond. Without a response-time agreement, the
  escalation is a log, not a rescue.
- **Rate limits at plant scale.** I hit Gemini's free-tier rate limit (429) while testing with
  rapid questions. One supervisor asking occasionally will be fine, but a whole shift asking at
  once could hit the same limit. The app retries and falls back gracefully, but a paid tier or a
  local model would be needed for real deployment.

### What I would ask the customer

- Who is the named human for escalations, and what is their contact (phone/radio)? What response
  time do you expect for an escalated question?
- Which procedures are safety-critical — should the app refuse to give steps for them entirely, or
  is showing the SOP with a warning banner (what I built) the right call?
- How do new SOP revisions reach the app? Who owns updating the documents, and how will I know
  when Rev05 of QC-SOP-014 exists?
- What devices do supervisors actually carry on the floor, and is the Wi-Fi reliable there? Are
  there areas where phones are restricted?
- What languages do your supervisors need? The sample SOPs are in English; is that enough?
- How do you want the audit log used — who reviews it, and how often?

### Challenges I faced while building and deploying, and how I handled them

- **The Drive folder link in the task brief had a typo.** The brief gave the folder ID with a
  single "p" (`...PALpItfcC...`); the real link in Pugazh's mail has a double "p"
  (`...PALppItfcC...`). The first lookup returned 404, which looked like the folder was
  unreachable. Instead of reporting it as unreachable, I read the original mail, took the link
  from there, and the folder opened. Lesson: when a shared link 404s, check the source message
  before concluding the resource is gone.
- **The Rev03 / Rev04 trap.** The sample set deliberately includes two revisions of QC-SOP-014,
  and Rev04 changes the sampling plan, makes the MTC mandatory, and moves quarantine. My first
  retrieval returned Rev04 chunks for most questions, but a question phrased exactly as Rev03
  states its rule ("draw 5 samples from every lot") initially got a bare "not found" instead of
  an explanation. I fixed it by passing supersession context into retrieval: when a retrieved
  chunk belongs to a document with a superseded revision, the best superseded chunk is included
  too, so the answer can explain that the old rule was replaced by Rev04. I also strengthened
  the generation prompt with an explicit rule — if the question describes a rule that appears
  only in a superseded passage, explain that it was the old revision and give the current
  revision's rule instead of saying "not found". The app now answers from the current revision
  and says so when an old rule is involved.
- **Gemini rate limiting (HTTP 429) while testing.** Rapid test questions hit the free-tier limit
  and the LLM calls failed. I added retry with backoff (2s, 5s) to the API client, and — more
  importantly — made the fallback conservative: if the LLM call fails, the app returns the
  retrieved passage only when the match is strong (score ≥ 0.60); otherwise it says "not found"
  instead of serving an irrelevant passage as if it were the answer. The app now degrades
  gracefully instead of failing or guessing.
- **The TF-IDF fallback ranked the wrong passage.** Without an API key the app uses TF-IDF, and
  it initially ranked document title/header chunks above the passages that answer the question
  (the header/footer text matched generic terms like "TX-200" and "CNC"). I stripped document
  furniture (title block, "Uncontrolled copy" footer) from the chunk text, added a phrase bonus
  for multi-word matches ("coolant concentration"), and made extractive mode honest in the UI
  ("most relevant passage — please verify") instead of presenting a passage as a definitive
  answer. The embedding + LLM path is the primary mode and is unaffected; the fallback is now a
  clearly-labelled degraded mode, and the README says so.
- **The biggest challenge overall: trust.** The technical build (FastAPI, RAG, retrieval) was
  straightforward. The hard part was the one the AI challenge named: making a tool that a
  supervisor can trust on a shop floor where a wrong answer can injure someone. I handled it by
  making the app show its sources on every answer, say "I don't know" instead of guessing, refuse
  to present itself as the authority for safety procedures, log everything for audit, and always
  give the supervisor a next step (a human) when it cannot answer. Whether that is enough is the
  open question above — but it is the right place to have spent the effort.

### The biggest challenge, in one line

Making the copilot *trustworthy* rather than merely *working* — a correct answer with its source
shown, an honest "I don't know" with a human to turn to, and an audit trail — because on a shop
floor a confident wrong answer is worse than no answer at all.

