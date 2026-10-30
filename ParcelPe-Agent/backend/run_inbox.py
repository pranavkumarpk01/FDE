"""Demo script: run the agent over today's inbox and show what it did.

    python run_inbox.py            # summary table
    python run_inbox.py --steps    # also show every step the agent took
    python run_inbox.py --id MSG-004 --steps   # just one message
"""
import argparse
import json

from app import config
from app.agent import SupportAgent
from app.store import Store

ICONS = {"AUTO_REPLY": "AUTO ", "NEEDS_APPROVAL": "HUMAN", "ESCALATE": "ESCAL", "ASK_CUSTOMER": "ASK  "}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", action="store_true", help="show each step of the agent loop")
    parser.add_argument("--id", help="process only this message id")
    args = parser.parse_args()

    inbox = json.loads((config.DATA_DIR / "inbox.json").read_text())
    if args.id:
        inbox = [m for m in inbox if m["id"] == args.id]

    store = Store()
    agent = SupportAgent(store)
    print(f"\nParcelPe support agent  |  LLM: {agent.llm.label}  |  mode: {config.MODE}"
          f"  |  action limits: {'ON' if config.ENABLE_ACTION_LIMITS else 'OFF'}\n")

    results = []
    for msg in inbox:
        r = agent.handle(msg)
        results.append(r)
        print(f"[{ICONS[r['decision']]}] {r['message_id']}  {r['intent']:<15} {r['reason']}")
        if args.steps:
            print(f"   Customer: {msg['text']}")
            for s in r["steps"]:
                print(f"   {s['step']:<28} {s['detail']}")
            print()

    total = len(results)
    auto = sum(r["decision"] == "AUTO_REPLY" for r in results)
    cost = sum(r["cost_inr"] for r in results)
    print("\n--- Summary -------------------------------------------")
    print(f"Messages handled      : {total}")
    print(f"Fully automated       : {auto} ({auto / total:.0%})")
    print(f"Waiting for a human   : {sum(r['decision'] in ('NEEDS_APPROVAL', 'ESCALATE') for r in results)}")
    print(f"Asked customer for info: {sum(r['decision'] == 'ASK_CUSTOMER' for r in results)}")
    print(f"LLM cost (₹)          : {cost:.2f}   vs human cost ≈ ₹{total * config.HUMAN_COST_PER_MESSAGE_INR:.0f}")
    print(f"Saved to              : {store.kind} (messages, tickets, refunds collections)\n")


if __name__ == "__main__":
    main()
