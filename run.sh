#!/bin/bash
# Run the SOP copilot on your laptop, reachable from your phone on the same Wi-Fi.
# Usage:
#   GOOGLE_API_KEY=your_key_here ./run.sh
#   (without a key the app still works — TF-IDF retrieval + extractive answers)
# Then open http://<your-laptop-IP>:8000 on your phone.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
echo "Starting SOP copilot on http://0.0.0.0:8000 ..."
echo "Your laptop's Wi-Fi address:"
if command -v hostname >/dev/null 2>&1; then hostname -I 2>/dev/null | awk '{print "  http://"$1":8000"}'; fi
if command -v ipconfig >/dev/null 2>&1; then ipconfig getifaddr en0 2>/dev/null | awk '{print "  http://"$1":8000"}'; fi
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
