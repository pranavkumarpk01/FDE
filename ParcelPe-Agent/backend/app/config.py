"""All the knobs of the system in one place. Change them in the .env file — no code changes."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # backend/
load_dotenv(ROOT.parent / ".env")                        # project-root .env
load_dotenv(ROOT / ".env")                               # or backend/.env

DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# --- The brain --------------------------------------------------------------
# "mock"   -> no API key needed, rule-based stand-in (safe for rehearsals)
# "gemini" -> Google Gemini (needs GEMINI_API_KEY)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-flash-latest")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- The database -----------------------------------------------------------
# Empty MONGO_URI -> in-memory database (nothing to install). Set it to use MongoDB.
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "parcelpe")

# --- Deployment mode --------------------------------------------------------
# "shadow" -> decide + draft, nothing is sent | "live" -> safe auto-replies are sent
MODE = os.getenv("MODE", "shadow").lower()

# --- Guardrails -------------------------------------------------------------
ENABLE_ACTION_LIMITS = os.getenv("ENABLE_ACTION_LIMITS", "true").lower() == "true"
REFUND_AUTO_LIMIT_INR = int(os.getenv("REFUND_AUTO_LIMIT_INR", "2000"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.7"))

# --- Economics --------------------------------------------------------------
PRICE_INPUT_PER_MTOK_INR = float(os.getenv("PRICE_INPUT_PER_MTOK_INR", "0"))
PRICE_OUTPUT_PER_MTOK_INR = float(os.getenv("PRICE_OUTPUT_PER_MTOK_INR", "0"))
HUMAN_COST_PER_MESSAGE_INR = float(os.getenv("HUMAN_COST_PER_MESSAGE_INR", "25"))
