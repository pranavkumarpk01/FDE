@echo off
REM ParcelPe AI Support Desk — one-command start on Windows. Double-click or run: start.bat
cd /d "%~dp0"
if not exist .env copy .env.example .env
cd backend
if not exist .venv\Scripts\uvicorn.exe (
  echo Installing Python packages ^(first run only^)...
  python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
start "" http://localhost:8000
.venv\Scripts\uvicorn app.api:app --port 8000
