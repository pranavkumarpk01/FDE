# Step 1 · Audit — find the right problem

> A doctor doesn't prescribe before diagnosing. Neither does an FDE.

## The client
**ParcelPe** (fictional) — a Bengaluru courier startup shipping across India.

## What we saw when we sat with the support team for a day
| What | Today |
|---|---|
| Messages per day | ~3,000 (WhatsApp + email) |
| Support agents | 8 |
| Tools they jump between | Inbox · tracking sheet · refund portal |
| Time to first reply | ~6 hours |
| Biggest money leak | Fake / repeat damage claims paid without checks |

## The workflow, as it really happens
```
Customer message ─► agent reads it ─► copies tracking ID into the tracking sheet
     ─► checks the refund rules in a PDF ─► opens the refund portal ─► types a reply
```
Every step is manual. Most messages are the same four questions.

## Pain points, ranked by cost
1. **"Where is my parcel?"** — the most common message, 100% copy-paste work.
2. **Refunds & damage claims** — slow, inconsistent, and the source of money leaks.
3. **Address changes** — easy, but often missed until it's too late.
4. **Everything else** — rare, needs a human.

## AI vs human — who does what
| Task | AI | Human |
|---|---|---|
| Understand the message (any language) | ✅ | |
| Look up tracking status | ✅ | |
| Apply the refund policy | ✅ (rules as code) | |
| Pay out ≤ ₹2,000, clean history | ✅ | |
| Pay out > ₹2,000 or flagged claim | drafts | ✅ approves |
| Odd or suspicious requests | | ✅ |

## Success metric we agreed with the client
- First reply in **under 10 minutes** (was 6 hours)
- **≥ 50%** of messages fully automated
- **Zero** unsafe payouts
