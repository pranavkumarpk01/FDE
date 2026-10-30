"""The agent loop — 7 steps for every customer message.

  1. Input guardrail   hide personal data, catch prompt injection
  2. Understand (LLM)  intent + tracking ID + confidence
  3. Act (tools)       track_parcel · check_refund_policy · photo_check · update_address
  4. Action guardrail  payout > ₹2,000 or flagged → human approval
  5. Draft reply (LLM) only from verified facts
  6. Output guardrail  no unapproved promises, no personal data
  7. Audit trail       everything saved to MongoDB

Each step is recorded with a `kind` (guard / ai / tool / log) and a `status`
(ok / warn / blocked) so the dashboard can animate it.
"""
import time
import uuid

from app import config, guardrails, tools
from app.llm import LLM
from app.store import Store

AUTO_REPLY = "AUTO_REPLY"          # AI handles it end to end
NEEDS_APPROVAL = "NEEDS_APPROVAL"  # AI drafts, a human approves
ESCALATE = "ESCALATE"              # straight to a human
ASK_CUSTOMER = "ASK_CUSTOMER"      # AI needs more information


class SupportAgent:
    def __init__(self, store: Store, llm: LLM | None = None, log: bool = True):
        self.store = store
        self.llm = llm or LLM()
        self.log = log

    def handle(self, message: dict) -> dict:
        started = time.time()
        msg_id = message.get("id") or f"MSG-{uuid.uuid4().hex[:6].upper()}"
        image_b64, image_mime = message.get("image_base64"), message.get("image_mime")
        steps, usage, facts = [], {"input_tokens": 0, "output_tokens": 0}, {}

        def step(n, name, detail, kind, status="ok"):
            steps.append({"n": n, "step": name, "detail": detail, "kind": kind, "status": status})

        def add(u):
            usage["input_tokens"] += u["input_tokens"]
            usage["output_tokens"] += u["output_tokens"]

        ctx = dict(message_id=msg_id, channel=message.get("channel", "whatsapp"),
                   has_image=bool(image_b64), steps=steps, usage=usage, started=started)

        # 1. INPUT GUARDRAIL ---------------------------------------------------
        text, pii = guardrails.mask_pii(message["text"])
        ctx["customer_text"] = text  # only the masked text is ever stored
        if pii:
            step(1, "Input guardrail", f"Personal data hidden before the AI sees it: {', '.join(pii)}", "guard", "warn")
        else:
            step(1, "Input guardrail", "No personal data found", "guard")
        if guardrails.looks_like_injection(text):
            step(1, "Input guardrail", "Prompt-injection attempt detected — the AI never acts on it", "guard", "blocked")
            return self._finish(ctx, ESCALATE, {"intent": "other"}, "prompt injection blocked")

        # 2. UNDERSTAND --------------------------------------------------------
        u, used = self.llm.understand(text)
        add(used)
        intent, tid = u.get("intent", "other"), u.get("tracking_id")
        conf = float(u.get("confidence", 0) or 0)
        if u.get("error"):
            step(2, "Understand (LLM)", u["error"] + " → handing to a human", "ai", "blocked")
            return self._finish(ctx, ESCALATE, {"intent": "other"}, "AI unavailable")
        step(2, "Understand (LLM)", f"intent = {intent} · tracking ID = {tid or '—'} · confidence = {conf:.2f}", "ai")
        facts.update({"intent": intent, "tracking_id": tid})
        if intent == "other":
            return self._finish(ctx, ESCALATE, facts, "not a standard request")
        if conf < config.MIN_CONFIDENCE:
            step(4, "Action guardrail", f"Confidence {conf:.2f} is below {config.MIN_CONFIDENCE}", "guard", "blocked")
            return self._finish(ctx, ESCALATE, facts, "low confidence")

        # 3. ACT — tools -------------------------------------------------------
        parcel = tools.track_parcel(self.store, tid) if tid else None
        if not parcel:
            step(3, "Tool · track_parcel", "No valid tracking ID — ask the customer", "tool", "warn")
            return self._finish(ctx, ASK_CUSTOMER, facts, "missing tracking ID")
        step(3, "Tool · track_parcel",
             f"{tid}: {parcel['status'].replace('_', ' ')} · {parcel['last_location']} · ETA {parcel['eta']}", "tool")
        facts.update({k: parcel.get(k) for k in ("customer", "status", "last_location", "eta", "days_late")})

        decision, reason, refund = AUTO_REPLY, "routine request handled by AI", 0

        if intent in ("refund_request", "damage_claim"):
            has_photo = bool(u.get("has_photo")) or bool(image_b64)
            flags_extra = []
            if intent == "damage_claim" and image_b64:
                photo, used = self.llm.check_photo(image_b64, image_mime)
                add(used)
                ok = bool(photo.get("shows_damage"))
                step(3, "Tool · photo_check", photo.get("description", ""), "tool", "ok" if ok else "warn")
                if not ok:
                    flags_extra.append("photo_does_not_show_damage")
            policy = tools.check_refund_policy(parcel, intent, has_photo)
            policy["flags"] += flags_extra
            step(3, "Tool · check_refund_policy",
                 f"eligible = {policy['eligible']} · amount = ₹{policy['amount_inr']:,} · "
                 f"flags = {', '.join(policy['flags']) or 'none'}", "tool")
            facts["policy_reason"] = policy["reason"]

            if policy["eligible"]:
                # 4. ACTION GUARDRAIL -------------------------------------------
                blockers = guardrails.needs_human_approval(policy["amount_inr"], policy["flags"], conf)
                if blockers:
                    decision, reason = NEEDS_APPROVAL, "; ".join(blockers)
                    step(4, "Action guardrail", "Human approval required — " + reason, "guard", "blocked")
                    facts["pending_amount_inr"] = policy["amount_inr"]
                else:
                    refund = policy["amount_inr"]
                    facts.update({"refund_status": "issued", "refund_amount_inr": refund})
                    step(4, "Action guardrail", f"₹{refund:,} is within the ₹{config.REFUND_AUTO_LIMIT_INR:,} "
                         "limit, no flags → AI may pay", "guard")
            else:
                step(4, "Action guardrail", "No payout — policy says not eligible", "guard")

        elif intent == "address_change":
            change = tools.update_address(self.store, parcel, u.get("new_address"))
            facts.update({"address_updated": change["updated"], "new_address": change["new_address"]})
            step(3, "Tool · update_address", "Address updated in the database" if change["updated"]
                 else "Not allowed — parcel already out for delivery", "tool", "ok" if change["updated"] else "warn")

        return self._finish(ctx, decision, facts, reason, refund=refund)

    # ------------------------------------------------------------------------
    def _finish(self, ctx, decision, facts, reason, refund=0):
        steps, usage = ctx["steps"], ctx["usage"]
        ticket = None
        if decision in (NEEDS_APPROVAL, ESCALATE):
            ticket = tools.create_ticket(
                self.store, message_id=ctx["message_id"], decision=decision, reason=reason,
                intent=facts.get("intent"), tracking_id=facts.get("tracking_id"),
                amount_inr=facts.get("pending_amount_inr", 0), customer_text=ctx["customer_text"])
            facts["ticket_id"] = ticket

        # 5. DRAFT REPLY ---------------------------------------------------------
        facts["decision"] = decision
        reply, used = self.llm.draft_reply(facts)
        usage["input_tokens"] += used["input_tokens"]
        usage["output_tokens"] += used["output_tokens"]
        steps.append({"n": 5, "step": "Draft reply (LLM)", "detail": reply, "kind": "ai", "status": "ok"})

        # 6. OUTPUT GUARDRAIL ----------------------------------------------------
        issues = guardrails.check_reply(reply, refund_issued=refund > 0)
        if issues:
            decision, reason = NEEDS_APPROVAL, "output check: " + "; ".join(issues)
            steps.append({"n": 6, "step": "Output guardrail", "detail": "Blocked — " + reason,
                          "kind": "guard", "status": "blocked"})
            refund = 0
        else:
            steps.append({"n": 6, "step": "Output guardrail", "detail": "Reply passed all checks",
                          "kind": "guard", "status": "ok"})

        if refund:
            self.store.record_refund(facts["tracking_id"], refund, approved_by="ai", message_id=ctx["message_id"])

        cost = (usage["input_tokens"] * config.PRICE_INPUT_PER_MTOK_INR
                + usage["output_tokens"] * config.PRICE_OUTPUT_PER_MTOK_INR) / 1_000_000
        result = {
            "message_id": ctx["message_id"], "channel": ctx["channel"], "customer_text": ctx["customer_text"],
            "has_image": ctx["has_image"], "intent": facts.get("intent"), "tracking_id": facts.get("tracking_id"),
            "decision": decision, "reason": reason, "ticket_id": ticket,
            "refund_issued": refund > 0, "refund_amount_inr": refund,
            "reply": reply, "sent_to_customer": decision in (AUTO_REPLY, ASK_CUSTOMER) and config.MODE == "live",
            "mode": config.MODE, "llm": self.llm.label, "tokens": usage, "cost_inr": round(cost, 4),
            "latency_ms": int((time.time() - ctx["started"]) * 1000), "steps": steps,
        }
        # 7. AUDIT TRAIL -----------------------------------------------------------
        steps.append({"n": 7, "step": "Audit trail", "detail": f"Saved to {self.store.kind} → messages collection",
                      "kind": "log", "status": "ok"})
        if self.log:
            self.store.save_message(dict(result))
        return result
