# Demo guide — what to click, what to say (~10 minutes)

## Before the talk (5 minutes)
1. Docker Desktop running → `docker compose up --build` (or start backend + frontend, see SETUP.md).
2. Open http://localhost:3000. Top bar should show **LLM gemini · …** and **DB mongodb**.
3. Press **Reset demo**.
4. Keep a damaged-parcel photo on your desktop for run 03.
5. Backup plan: if Wi-Fi or Gemini fails, set `LLM_PROVIDER=mock` in `.env` and restart. Same demo, works offline.

## Opening line
> "This is ParcelPe's support desk. On the left is a customer's phone. In the middle is what happens inside the AI. On the right is exactly what gets saved in the database. Watch the 7 steps."

## Run 01 — Prompt attack
Click **01 Prompt attack** → send.
- Step 1 turns red. "The AI never even saw an instruction it could act on."
- Verdict: **Blocked · escalated**. A ticket is created for a human.
> "Anyone can type anything into WhatsApp. The first guardrail runs before the AI."

## Run 02 — Aadhaar & phone
Click **02** → send.
- Step 1 turns amber: *Personal data hidden: AADHAAR, PHONE*.
- Point to the right panel: `customer_text` says `[AADHAAR]` and `[PHONE]`.
> "The AI and the database never see the real number. That's what makes this deployable in a bank or a logistics company."

## Run 03 — Refund ₹1,200 with a photo
Click **03**, press **＋**, attach the photo → send.
- Step 3 shows `photo_check` and the policy: eligible, ₹1,200.
- Step 4: *within the ₹2,000 limit → AI may pay*.
- Verdict: **Auto-resolved by AI · ₹1,200 refunded automatically**.
> "Small, clear, policy-backed cases: the AI just does it. No queue, no waiting."

## Run 04 — Refund ₹7,400
Click **04** → send.
- Step 4 turns red: *payout ₹7,400 is above the ₹2,000 auto-limit*.
- Verdict: **Sent to a human**.
- Go to **Ops console** → the ticket → press **Approve**. Refunds table: *approved by support lead*.
> "The AI did 90% of the work — found the parcel, checked the policy, drafted the reply. The human just clicks approve."

**Optional wow moment:** switch the **₹2,000 guardrail OFF** in the top bar, go back, rerun 04 → the AI pays ₹7,400 alone. Switch it back ON.
> "That one switch is the difference between a demo and a production system."

## Run 05 — Where's my order?
Click **05** → send. Instant answer from the tracking tool.
> "This is 40% of ParcelPe's messages. Gone from the human queue."

## Close with Ops console + Evals
- **Ops console**: automation rate, guardrail stops, ₹ refunded by AI vs humans, AI cost vs human cost.
- **Evals** → **Run evals** → 20/20, 0 unsafe. Flip the guardrail OFF → run again → unsafe outcomes appear.
> "This is the exam the AI takes before every release. Zero unsafe, or it doesn't ship."

## If someone asks…
| Question | Answer |
|---|---|
| What if the photo is fine and the refund is ₹1,200? | Under ₹2,000, photo present, within 48 hours, no flags → AI refunds ₹1,200 and logs it. If Gemini sees the photo doesn't show damage, it's flagged → human. |
| What if Gemini goes down? | Every message goes to a human. Nothing breaks, nothing wrong gets sent. |
| Where is the data? | MongoDB: `parcels`, `messages`, `tickets`, `refunds`. Open http://localhost:8081. |
| How do you change the ₹2,000 limit? | `.env` → `REFUND_AUTO_LIMIT_INR`. No code change. |
| How does it go live? | Shadow mode first (AI drafts, humans send), then 5% → 25% → everyone. |
