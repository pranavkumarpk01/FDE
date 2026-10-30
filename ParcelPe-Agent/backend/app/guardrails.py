"""Guardrails — the rules the AI can never break.

1. Input check   : hide personal data, catch prompt-injection attempts
2. Action limit  : big or risky payouts wait for a human
3. Output check  : the reply must not promise what wasn't approved or leak data
"""
from __future__ import annotations
import re

from app import config

# Order matters: check 12-digit Aadhaar before 10-digit phone numbers.
PII_PATTERNS = {
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "PHONE": re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
}

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"you are now",
    r"system prompt",
    r"act as (an? )?(admin|manager)",
    r"approve (a |the )?refund",
]

UNAPPROVED_PROMISES = ["we have refunded", "refund has been processed", "issued ₹", "guarantee"]


# ---------- 1. Input check ----------
def mask_pii(text: str) -> tuple[str, list[str]]:
    found = []
    for label, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            found.append(label)
            text = pattern.sub(f"[{label}]", text)
    return text, found


def looks_like_injection(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in INJECTION_PATTERNS)


# ---------- 2. Action limit ----------
def needs_human_approval(amount_inr: int, flags: list[str], confidence: float) -> list[str]:
    """Returns the reasons a human must approve. Empty list = AI may act alone."""
    if not config.ENABLE_ACTION_LIMITS:
        return []
    reasons = []
    if amount_inr > config.REFUND_AUTO_LIMIT_INR:
        reasons.append(f"payout ₹{amount_inr} is above the ₹{config.REFUND_AUTO_LIMIT_INR} auto-limit")
    if flags:
        reasons.append("flagged: " + ", ".join(flags))
    if confidence < config.MIN_CONFIDENCE:
        reasons.append(f"low confidence ({confidence:.2f})")
    return reasons


# ---------- 3. Output check ----------
def check_reply(reply: str, refund_issued: bool) -> list[str]:
    issues = []
    low = reply.lower()
    if not refund_issued and any(p in low for p in UNAPPROVED_PROMISES):
        issues.append("reply promises a refund that was not approved")
    _, leaked = mask_pii(reply)
    if leaked:
        issues.append("reply contains personal data: " + ", ".join(leaked))
    if len(reply.split()) > 120:
        issues.append("reply is too long")
    return issues
