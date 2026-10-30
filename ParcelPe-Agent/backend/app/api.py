"""The backend web service (FastAPI). The React frontend talks to these endpoints.

Interactive docs: http://localhost:8000/docs
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import config
from app.agent import SupportAgent
from app.store import Store
from evals.run_evals import evaluate

app = FastAPI(title="ParcelPe Support Agent API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = Store()
agent = SupportAgent(store)


class Message(BaseModel):
    id: Optional[str] = None
    channel: str = "whatsapp"
    text: str
    image_base64: Optional[str] = None   # optional photo, base64 (no data: prefix)
    image_mime: Optional[str] = None


class Settings(BaseModel):
    enable_action_limits: Optional[bool] = None
    mode: Optional[str] = None


# ---------------- Agent ----------------
@app.get("/api/health")
def health():
    return {"status": "ok", "llm": agent.llm.label, "database": store.kind, "mode": config.MODE}


@app.post("/api/messages")
def handle_message(msg: Message):
    """Send one customer message to the agent. Returns the decision, reply and every step."""
    return agent.handle(msg.model_dump())


@app.get("/api/messages")
def list_messages(limit: int = 100):
    """The audit trail — latest first (MongoDB `messages` collection)."""
    return store.list_messages(limit)


@app.get("/api/inbox")
def inbox():
    return json.loads((config.DATA_DIR / "inbox.json").read_text())


# ---------------- Humans ----------------
@app.get("/api/tickets")
def tickets(status: Optional[str] = None):
    """The human review queue (MongoDB `tickets` collection). status = open | approved | rejected"""
    return store.list_tickets(status)


@app.post("/api/tickets/{ticket_id}/approve")
def approve(ticket_id: str):
    t = store.get_ticket(ticket_id)
    if not t:
        raise HTTPException(404, "ticket not found")
    store.set_ticket_status(ticket_id, "approved")
    if t.get("amount_inr"):
        store.record_refund(t["tracking_id"], t["amount_inr"], approved_by="support lead", message_id=t["message_id"])
    return store.get_ticket(ticket_id)


@app.post("/api/tickets/{ticket_id}/reject")
def reject(ticket_id: str):
    if not store.get_ticket(ticket_id):
        raise HTTPException(404, "ticket not found")
    store.set_ticket_status(ticket_id, "rejected")
    return store.get_ticket(ticket_id)


# ---------------- Data & monitoring ----------------
@app.get("/api/parcels")
def parcels():
    return store.list_parcels()


@app.get("/api/refunds")
def refunds():
    return store.list_refunds()


@app.get("/api/metrics")
def metrics():
    return store.metrics()


# ---------------- Testing & settings ----------------
@app.post("/api/evals/run")
def run_evals():
    return evaluate(llm=agent.llm)


@app.get("/api/settings")
def get_settings():
    return {"enable_action_limits": config.ENABLE_ACTION_LIMITS, "mode": config.MODE,
            "llm": agent.llm.label, "database": store.kind,
            "refund_auto_limit_inr": config.REFUND_AUTO_LIMIT_INR}


@app.post("/api/settings")
def set_settings(s: Settings):
    if s.enable_action_limits is not None:
        config.ENABLE_ACTION_LIMITS = s.enable_action_limits
    if s.mode in ("shadow", "live"):
        config.MODE = s.mode
    return get_settings()


@app.post("/api/reset")
def reset():
    """Clear messages, tickets and refunds; re-seed parcels. Fresh demo."""
    store.reset()
    return {"status": "reset", "database": store.kind}


# ---------------- The web app ----------------
# If the React app has been built (frontend/dist), serve it here too,
# so ONE command gives you everything at http://localhost:8000
WEB = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
