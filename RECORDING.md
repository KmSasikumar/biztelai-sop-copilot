# Recording script — SOP Copilot demo (2–3 minutes)

This is the screen recording for the BiztelAI assignment. It shows three things:
1. The app answering **2 sample questions**.
2. The app responding to a question the **documents cannot answer**.
3. The app opened and **used from a phone**.

Record it in one take on your laptop (screen + voice), then switch to your phone
for the last part. Total target: **2–3 minutes**. Speak naturally — you are showing
a supervisor's tool, not presenting slides.

---

## Before you record (5 minutes, do this once)

1. **Get a free Gemini API key** (so the app gives clean LLM answers, not passages):
   - Open https://aistudio.google.com/apikey in your browser, sign in with your
     Google account, click **Create API key**. Copy the key.
   - Keep the key private — never paste it into the recording or the repo.
2. **Start the app** from the repo folder:
   ```bash
   cd biztelai-sop-copilot
   GOOGLE_API_KEY=<redacted> ./run.sh
   ```
   (On Windows, use `set GOOGLE_API_KEY=<redacted>` first, then `run.bat` — see
   README. Without a key the app still works, but answers are passages, not
   clean answers, so use the key for the recording.)
3. **Note the phone address** the script prints, e.g. `http://192.168.1.5:8000`.
   Keep that tab open on your laptop.
4. **Phone:** connect your phone to the **same Wi-Fi** as your laptop. Open the
   phone address from step 3 in the phone browser and confirm the app loads.
   Leave the phone on the home screen of the app, ready to tap.
5. **Start your screen recorder** (Windows: Win + G / Snipping Tool; macOS:
   Cmd + Shift + 5; or use your phone to record the laptop screen).

---

## The recording (one take, ~2–3 min)

### Part 1 — Two sample questions (about 1 minute, on the laptop)

Say, in your own words: *"This is the SOP Copilot. A supervisor on the shop floor
asks a question and gets the answer from the plant's SOPs, with the source shown."*

Then ask these two questions, one at a time, waiting for each answer:

**Q1 (type or tap the chip):** "What is the recommended coolant concentration
for the TX-200 CNC turning centre?"
- Expected answer: **6–8%** (refractometer reading × 1.0 factor).
- Point at the source line under the answer: **MNT-MAN-CNC-02, Rev 02**.

**Q2:** "The machine is showing alarm AL-104. What does it mean and what should
the operator do?"
- Expected answer: **Way lube oil level low — top up with ISO VG 68 to the MAX
  mark, press RESET, machine can continue.**
- Point at the source: **MNT-MAN-CNC-02, Rev 02**.

### Part 2 — A question the documents cannot answer (about 30 seconds, laptop)

Say: *"And when the answer is not in the documents, it says so instead of guessing."*

**Q3:** "What is the overtime rate for a maintenance technician working a Sunday shift?"
- Expected answer: **"I couldn't find this in the provided documents."**
- Then tap **"Send this question to my supervisor"** and show the confirmation:
  it is logged and routed to the **Shift QC Supervisor / Safety Officer**.
  Say: *"So the question is not lost — it goes to a named human."*

### Part 3 — From the phone (about 45 seconds)

Say: *"The same app, on a phone on the shop floor."*

Pick up your phone (already on the app's home screen). Ask one question —
use **Q2 (AL-104)** again or **"Who is allowed to remove a lockout lock from a
machine?"** (expected: **each authorised person removes only their own lock**,
with the safety warning banner shown).
- Show the answer and its source on the phone screen.
- If you can, hold the phone so the laptop screen is visible behind it, or
  record the phone screen directly — either is fine.

End by saying: *"That is the SOP Copilot — answers from the SOPs, sources shown,
and a human to turn to when it does not know."* Stop recording.

---

## After recording

- Upload the video to **Google Drive** (or Loom) and share the link in your
  Wellfound submission alongside the repo link:
  **https://github.com/KmSasikumar/biztelai-sop-copilot**
- If any answer in the recording differs from the expected answers above, stop
  and check: is the API key set? Is the server running from the repo folder?
  The README's "My 5 questions" section lists the verified answers.

## If something goes wrong while recording

- **App does not load on the phone:** check the phone and laptop are on the
  **same Wi-Fi**, and that the laptop firewall allows port 8000. Re-run
  `run.sh` and use the address it prints.
- **Answer is a long passage, not a short answer:** the API key is not set —
  stop, set `GOOGLE_API_KEY`, and restart the server.
- **"I couldn't find this" for a question that should work:** the server may
  have hit a rate limit — wait a minute and ask again.
