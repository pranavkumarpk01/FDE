# Step 3 · Deploy — from laptop to the real business

## 1. Connect
Swap the seeded `parcels` collection and the functions in `backend/app/tools.py` for ParcelPe's real tracking API, refund system and ticketing tool. Nothing else changes.

## 2. Sandbox
Run the agent on last month's messages (`backend/run_inbox.py`) and the golden dataset (`backend/evals/`). No real customers.

## 3. Shadow mode — `MODE=shadow` (the default)
The agent decides and drafts, but **nothing is sent**. Support agents keep working as usual and compare the AI's draft with what they actually sent. Everything is in MongoDB → `messages` collection, visible in the Ops console.

## 4. Roll out slowly — `MODE=live`
| Week | Share of messages | Moves on when |
|---|---|---|
| 1 | Shadow only | AI matches humans on most past cases |
| 2 | 5% — tracking questions only | No complaints, humans rarely edit drafts |
| 3 | 25% — tracking + small refunds | Zero unsafe payouts |
| 4+ | Everyone | Metrics stay green |

## 5. Monitor
- **Ops console** (http://localhost:3000) — KPIs, review queue, audit trail, refunds
- `GET /api/metrics` — automation rate, guardrail stops, refunds by AI vs humans, LLM vs human cost, latency
- `GET /api/tickets?status=open` — what's waiting for a human
- MongoDB `messages` collection — why every decision was made

## 6. Ship it
`docker compose up -d --build` on any VM. In production: Gemini key in a secret manager, MongoDB Atlas with backups, HTTPS in front, ports 8081/27017 kept private. Full steps in `SETUP.md`.

## Economics (fill in after a real-LLM run)
| | Value |
|---|---|
| LLM cost per message | ₹___ (from the eval report) |
| Human cost per message | ₹25 (assumption — confirm with client) |
| Messages automated per day | ~50% of 3,000 |
