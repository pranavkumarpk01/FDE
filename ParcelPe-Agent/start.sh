#!/bin/bash
# ParcelPe AI Support Desk — one-command start.
#   bash start.sh
# Then open http://localhost:8000  (it opens by itself on a Mac). Stop with Ctrl+C.
set -e
cd "$(dirname "$0")"

# 1. Settings file + Gemini key (asked once, saved in .env)
[ -f .env ] || cp .env.example .env
sed -i.bak -e 's/^LLM_PROVIDER=mock/LLM_PROVIDER=gemini/' -e 's/^LLM_MODEL=gemini-flash-latest/LLM_MODEL=gemini-2.5-flash/' .env && rm -f .env.bak
KEY=$(grep '^GEMINI_API_KEY=' .env | cut -d= -f2- | tr -d ' "')
if [ -z "$KEY" ]; then
  echo ""
  read -r -p "Paste your Gemini API key (from aistudio.google.com/apikey): " KEY
  sed -i.bak "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$KEY|" .env && rm -f .env.bak
  echo "Saved in .env"
fi

# 2. Python packages (first run only, ~1 minute)
cd backend
if [ ! -x .venv/bin/uvicorn ]; then
  echo "Installing Python packages (first run only)..."
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

# 3. Check Gemini answers before opening the app
echo "Checking Gemini..."
if .venv/bin/python -c "
import sys
from app.llm import LLM
llm = LLM()
r, u = llm.understand('Hi, where is my parcel PP100231?')
if r.get('error'): print('  ✗', r['error']); sys.exit(1)
print('  ✓', llm.label, 'is working →', r.get('intent'), r.get('tracking_id'))
" 2>/dev/null; then :; else
  echo "  ✗ Gemini did not answer. Check GEMINI_API_KEY and LLM_MODEL in .env, and your internet."
  echo "    The app will still open, but every message will go to a human."
fi

# 4. Start
PORT=${PORT:-8000}
echo ""
echo "  ParcelPe AI Support Desk  →  http://localhost:$PORT"
echo "  Stop with Ctrl+C"
echo ""
( sleep 3; command -v open >/dev/null && open "http://localhost:$PORT" >/dev/null 2>&1 ) &
exec .venv/bin/uvicorn app.api:app --port "$PORT"
