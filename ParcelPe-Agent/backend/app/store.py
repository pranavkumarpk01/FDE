"""The database layer — everything the system remembers lives here.

MongoDB collections:
  parcels   the tracking system (seeded from data/parcels.json)
  messages  the audit trail: every message, every step, every decision
  tickets   the human review queue
  refunds   every payout — automatic or approved by a human

If MONGO_URI is empty (or MongoDB is down), the same code runs on an
in-memory database (mongomock), so rehearsals and evals never break.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone

import mongomock
from pymongo import DESCENDING, MongoClient

from app import config


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, uri: str | None = None, in_memory: bool = False):
        uri = config.MONGO_URI if uri is None else uri
        self.kind = "in-memory"
        client = None
        if uri and not in_memory:
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=2500)
                client.admin.command("ping")
                self.kind = "mongodb"
            except Exception as exc:  # MongoDB not reachable -> keep the demo alive
                print(f"[store] MongoDB not reachable ({exc}); using in-memory database")
                client = None
        self.client = client or mongomock.MongoClient()
        self.db = self.client[config.MONGO_DB]
        self.seed_parcels()

    # ---------------- parcels ----------------
    def seed_parcels(self, force: bool = False) -> None:
        if force:
            self.db.parcels.delete_many({})
        if self.db.parcels.count_documents({}) == 0:
            parcels = json.loads((config.DATA_DIR / "parcels.json").read_text())
            self.db.parcels.insert_many(parcels)
            self.db.parcels.create_index("tracking_id", unique=True)

    def get_parcel(self, tracking_id: str) -> dict | None:
        return self.db.parcels.find_one({"tracking_id": (tracking_id or "").upper()}, {"_id": 0})

    def list_parcels(self) -> list[dict]:
        return list(self.db.parcels.find({}, {"_id": 0}).sort("tracking_id"))

    def update_parcel(self, tracking_id: str, changes: dict) -> None:
        self.db.parcels.update_one({"tracking_id": tracking_id}, {"$set": changes})

    # ---------------- messages (audit trail) ----------------
    def save_message(self, result: dict) -> None:
        self.db.messages.insert_one({**result, "logged_at": now()})

    def list_messages(self, limit: int = 100) -> list[dict]:
        return list(self.db.messages.find({}, {"_id": 0}).sort("logged_at", DESCENDING).limit(limit))

    # ---------------- tickets (human review queue) ----------------
    def create_ticket(self, doc: dict) -> str:
        ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"
        self.db.tickets.insert_one({"ticket_id": ticket_id, "status": "open", "created_at": now(), **doc})
        return ticket_id

    def list_tickets(self, status: str | None = None) -> list[dict]:
        query = {"status": status} if status else {}
        return list(self.db.tickets.find(query, {"_id": 0}).sort("created_at", DESCENDING))

    def get_ticket(self, ticket_id: str) -> dict | None:
        return self.db.tickets.find_one({"ticket_id": ticket_id}, {"_id": 0})

    def set_ticket_status(self, ticket_id: str, status: str, by: str = "support lead") -> None:
        self.db.tickets.update_one({"ticket_id": ticket_id},
                                   {"$set": {"status": status, "resolved_by": by, "resolved_at": now()}})

    # ---------------- refunds ----------------
    def record_refund(self, tracking_id: str, amount_inr: int, approved_by: str, message_id: str) -> None:
        self.db.refunds.insert_one({"tracking_id": tracking_id, "amount_inr": amount_inr,
                                    "approved_by": approved_by, "message_id": message_id, "paid_at": now()})

    def list_refunds(self) -> list[dict]:
        return list(self.db.refunds.find({}, {"_id": 0}).sort("paid_at", DESCENDING))

    # ---------------- monitoring ----------------
    def metrics(self) -> dict:
        msgs = list(self.db.messages.find({}, {"_id": 0, "decision": 1, "cost_inr": 1, "latency_ms": 1}))
        total = len(msgs)
        by_decision: dict[str, int] = {}
        for m in msgs:
            by_decision[m["decision"]] = by_decision.get(m["decision"], 0) + 1
        refunds = self.list_refunds()
        return {
            "messages": total,
            "by_decision": by_decision,
            "automation_rate": round(by_decision.get("AUTO_REPLY", 0) / total, 2) if total else 0,
            "open_tickets": self.db.tickets.count_documents({"status": "open"}),
            "approved_tickets": self.db.tickets.count_documents({"status": "approved"}),
            "guardrail_blocks": by_decision.get("ESCALATE", 0) + by_decision.get("NEEDS_APPROVAL", 0),
            "refunds_auto_inr": sum(r["amount_inr"] for r in refunds if r["approved_by"] == "ai"),
            "refunds_human_inr": sum(r["amount_inr"] for r in refunds if r["approved_by"] != "ai"),
            "llm_cost_inr": round(sum(m.get("cost_inr", 0) for m in msgs), 2),
            "human_cost_inr": round(total * config.HUMAN_COST_PER_MESSAGE_INR, 2),
            "avg_latency_ms": int(sum(m.get("latency_ms", 0) for m in msgs) / total) if total else 0,
        }

    def reset(self) -> None:
        for name in ("messages", "tickets", "refunds"):
            self.db[name].delete_many({})
        self.seed_parcels(force=True)
