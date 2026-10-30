"""The AI brain. Two providers:

- mock:   rule-based stand-in so the demo runs offline, free, and the same every time
- gemini: Google Gemini (text + photo understanding)

Every call returns (result, usage) so we can track cost per message.
"""
from __future__ import annotations
import base64
import time
import json
import re

from app import config
from app.prompts import PHOTO_CHECK_SYSTEM, REPLY_SYSTEM, UNDERSTAND_SYSTEM

TRACKING_RE = re.compile(r"\bPP\d{6}\b", re.IGNORECASE)


class LLM:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or config.LLM_PROVIDER).lower()
        self.model = model or config.LLM_MODEL
        self.client = None
        if self.provider == "gemini":
            from google import genai
            if not config.GEMINI_API_KEY:
                raise ValueError("Set GEMINI_API_KEY in your .env file")
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        elif self.provider != "mock":
            raise ValueError(f"Unknown LLM_PROVIDER: {self.provider} (use mock or gemini)")

    @property
    def label(self) -> str:
        return "mock" if self.provider == "mock" else f"gemini · {self.model}"

    # ---------- used by the agent ----------
    def understand(self, message: str) -> tuple[dict, dict]:
        if self.provider == "mock":
            return _mock_understand(message), _zero()
        try:
            text, usage = self._gemini(UNDERSTAND_SYSTEM, [message], json_mode=True)
        except Exception as e:  # bad key, quota, network... fail safe: a human takes over
            return {"intent": "other", "tracking_id": None, "confidence": 0.0,
                    "error": f"AI unavailable ({type(e).__name__}): {str(e)[:120]}"}, _zero()
        return _parse_json(text), usage

    def draft_reply(self, facts: dict) -> tuple[str, dict]:
        if self.provider == "mock":
            return _mock_reply(facts), _zero()
        try:
            text, usage = self._gemini(REPLY_SYSTEM, [json.dumps(facts, ensure_ascii=False)])
        except Exception:  # fall back to a safe template reply
            return _mock_reply(facts), _zero()
        return text.strip() or _mock_reply(facts), usage

    def check_photo(self, image_b64: str, mime: str) -> tuple[dict, dict]:
        """Does the customer's photo really show damage?"""
        if self.provider == "mock":
            return {"shows_damage": True, "description": "Mock check: photo accepted"}, _zero()
        from google.genai import types
        part = types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type=mime or "image/jpeg")
        try:
            text, usage = self._gemini(PHOTO_CHECK_SYSTEM, ["Check this damage-claim photo.", part], json_mode=True)
        except Exception:
            return {"shows_damage": False, "description": "Photo check unavailable — a human will look"}, _zero()
        return _parse_json(text, default={"shows_damage": False, "description": "Could not read the photo"}), usage

    # ---------- Gemini plumbing ----------
    def _gemini(self, system: str, contents: list, json_mode: bool = False) -> tuple[str, dict]:
        from google.genai import types
        cfg = {"system_instruction": system, "temperature": 0.2, "max_output_tokens": 4096}
        if json_mode:
            cfg["response_mime_type"] = "application/json"
        # Gemini 2.5 Flash "thinks" before answering; for triage we want fast, direct answers.
        if "2.5-flash" in self.model:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        last = None
        for attempt in range(2):  # one retry for a busy server / a model that rejects a setting
            try:
                resp = self.client.models.generate_content(model=self.model, contents=contents,
                                                           config=types.GenerateContentConfig(**cfg))
                meta = resp.usage_metadata
                return resp.text or "", {"input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
                                         "output_tokens": getattr(meta, "candidates_token_count", 0) or 0}
            except Exception as e:
                last = e
                cfg.pop("thinking_config", None)
                time.sleep(1)
        raise last


def _zero() -> dict:
    return {"input_tokens": 0, "output_tokens": 0}


def _parse_json(text: str, default: dict | None = None) -> dict:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return default or {"intent": "other", "tracking_id": None, "confidence": 0.0, "summary": "Unreadable model output"}


# ---------------------------------------------------------------------------
# Mock brain: simple keyword rules. Good enough to demo the whole flow offline.
# ---------------------------------------------------------------------------
KEYWORDS = {
    "damage_claim": ["damaged", "damage", "broken", "crushed", "cracked", "torn", "toot"],
    "refund_request": ["refund", "money back", "paisa wapas", "compensate"],
    "address_change": ["change address", "change the delivery address", "address for", "new address"],
    "track_parcel": ["where", "kahan", "kab", "status", "track", "late", "not arrived", "never arrived", "eta"],
}
INJECTION_HINTS = ["ignore all previous", "ignore previous", "approve a refund"]


def _mock_understand(message: str) -> dict:
    low = message.lower()
    found = TRACKING_RE.search(message)
    tracking_id = found.group(0).upper() if found else None
    if any(h in low for h in INJECTION_HINTS):
        return {"intent": "other", "tracking_id": tracking_id, "new_address": None, "has_photo": False,
                "confidence": 0.95, "summary": "Message tries to change the assistant's rules"}
    intent, confidence = "other", 0.5
    for name, words in KEYWORDS.items():  # order matters: damage > refund > address > track
        if any(w in low for w in words):
            intent, confidence = name, 0.9
            break
    if intent == "track_parcel" and any(w in low for w in KEYWORDS["refund_request"]):
        intent = "refund_request"
    new_address = None
    if intent == "address_change":
        m = re.search(r"\bto (.+?)(?:\.|$| please)", message, re.IGNORECASE)
        new_address = m.group(1).strip() if m else None
    return {"intent": intent, "tracking_id": tracking_id, "new_address": new_address,
            "has_photo": "photo" in low, "confidence": confidence,
            "summary": f"Customer message classified as {intent}"}


def _mock_reply(f: dict) -> str:
    name, tid, d = f.get("customer", "there"), f.get("tracking_id", ""), f["decision"]
    if d == "ASK_CUSTOMER":
        return ("Hi! We'd love to help. Could you share your ParcelPe tracking ID "
                "(it starts with PP, e.g. PP123456)? We'll check right away.")
    if d == "ESCALATE":
        return (f"Thanks for reaching out. A ParcelPe support specialist will look into this "
                f"(ticket {f.get('ticket_id')}) and get back to you within 24 hours.")
    if d == "NEEDS_APPROVAL":
        return (f"Hi {name}, sorry about the trouble with {tid}. We've raised your request "
                f"(ticket {f.get('ticket_id')}). A support specialist will review it and get back "
                "to you within 24 hours.")
    intent = f["intent"]
    if intent == "track_parcel":
        late = f" It's running {f['days_late']} days late — sorry about that." if f.get("days_late") else ""
        return (f"Hi {name}! Your parcel {tid} is {f['status'].replace('_', ' ')} — last seen at "
                f"{f['last_location']}. Expected delivery: {f['eta']}.{late}")
    if intent in ("refund_request", "damage_claim"):
        if f.get("refund_status") == "issued":
            return (f"Hi {name}, sorry about {tid}. As per our policy we've issued ₹{f['refund_amount_inr']} "
                    "to your original payment method. It should reflect in 3–5 working days.")
        return f"Hi {name}, we checked {tid}. {f.get('policy_reason', '')}"
    if intent == "address_change":
        if f.get("address_updated"):
            return f"Done, {name}! {tid} will now be delivered to: {f['new_address']}."
        return (f"Sorry {name}, {tid} is already {f['status'].replace('_', ' ')}, so the address "
                "can't be changed now. Our delivery partner will call before arriving.")
    return "Thanks for writing to ParcelPe! A support specialist will get back to you shortly."
