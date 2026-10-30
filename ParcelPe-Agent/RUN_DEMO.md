# Run the demo — the simple way

You only need **Python 3** (already on most Macs) and your **Gemini API key**. No Docker, no MongoDB, no Node.

## 1. Start it
Open Terminal in this folder and run:

```bash
bash start.sh
```

- First time: it asks for your **Gemini API key** (paste it, press Enter — saved in `.env`), then installs what it needs (about 1 minute).
- It checks Gemini answers: you should see `✓ gemini · gemini-2.5-flash is working`.
- Then the browser opens **http://localhost:8000** by itself. The top bar shows **LLM gemini · gemini-2.5-flash**.
- To stop: press **Ctrl + C** in Terminal.

(Windows: double-click `start.bat`.)

## 2. Before you go on stage
1. Click **Reset demo** (top right) so the screens are empty.
2. Keep any photo of a broken item on your desktop (for case 03).
3. Check the top bar shows **₹2,000 guardrail ON**.

## 3. The 5 cases
Click a card at the top → press the green send button → watch the 7 steps light up.

| Click | What the room sees |
|---|---|
| **01 Prompt attack** | Step 1 turns **red**. “Blocked · escalated” — the AI never acted on the trick. |
| **02 Aadhaar & phone** | Right panel shows `[AADHAAR]` and `[PHONE]` — the real numbers are never stored. |
| **03 Refund ₹1,200** | Press **＋** to attach the photo first. Under ₹2,000 → “₹1,200 refunded automatically”. |
| **04 Refund ₹7,400** | Step 4 turns **red** → “Sent to a human”. Open **Ops console** → press **Approve**. |
| **05 Where’s my order?** | Instant tracking answer. |

**Bonus:** switch the ₹2,000 guardrail **OFF** in the top bar, rerun 04 → the AI pays ₹7,400 on its own. Switch it back **ON**. Then **Evals** tab → **Run evals** → 20/20, 0 unsafe.

## Show that it's a real LLM, not rules
Type these yourself in the chat — no card, nothing pre-written:

- `Bro PP100231 innu bandilla, yaavaga barutte?` (Kannada + English) → it understands it's a tracking question.
- `Mera parcel PP100239 kab aayega? Bahut late ho gaya` (Hindi) → same, and replies politely.
- `Change the delivery address for PP100239 to 45 Church Street, Bengaluru` → updates the address.

Step 2 shows what Gemini understood, in its own words, with a confidence score. Step 3 for photo claims shows Gemini describing the photo.
Ask the room for a message and type it live — that's the most convincing moment.

## Good to know
- Use a **real photo of something broken** for case 03 — Gemini actually looks at it. A photo with no damage gets flagged and goes to a human (that's a feature — show it!).
- Each message takes 2–5 seconds (it's calling Gemini).
- The **Evals** tab runs 20 test messages through Gemini (~45 calls). On the free tier this can take a minute or hit the rate limit — run it once before the talk, not live.
- To change the model: edit `LLM_MODEL=` in `.env` (e.g. `gemini-flash-latest`) and restart.

## Something wrong?
| Problem | Fix |
|---|---|
| `python3: command not found` | Install Python from python.org, then run again |
| “Address already in use” | Run `PORT=8001 bash start.sh` and open http://localhost:8001 |
| Page is blank | Wait 5 seconds and refresh |
| Every message says “AI unavailable” | Wrong key, no internet, or rate limit. Fix the key in `.env`, or wait a minute |
| “✗ Gemini did not answer” at start | Same as above. Try `LLM_MODEL=gemini-flash-latest` in `.env` if the model name is the problem |
