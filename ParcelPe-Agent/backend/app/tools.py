"""The agent's 'hands' — functions that talk to ParcelPe's systems (here: MongoDB).

  track_parcel         look up status, location, ETA
  check_refund_policy  apply data/refund_policy.md as code
  photo_check          (in agent.py) Gemini looks at the damage photo
  update_address       change the delivery address, if still allowed
  create_ticket        hand over to a human (the review queue)
"""
from __future__ import annotations
from app.store import Store

DECLARED_VALUE_CAP_INR = 10_000


def track_parcel(store: Store, tracking_id: str) -> dict | None:
    return store.get_parcel(tracking_id)


def check_refund_policy(parcel: dict, intent: str, has_photo: bool) -> dict:
    status, flags = parcel["status"], []

    if intent == "damage_claim":
        if status != "delivered":
            return {"eligible": False, "amount_inr": 0, "flags": flags,
                    "reason": "Damage claims can be raised only after delivery."}
        if (parcel.get("delivered_hours_ago") or 0) > 48:
            return {"eligible": False, "amount_inr": 0, "flags": flags,
                    "reason": "Damage claims must be raised within 48 hours of delivery."}
        if not has_photo:
            return {"eligible": False, "amount_inr": 0, "flags": flags,
                    "reason": "Please share a photo of the damage so we can process the claim."}
        if parcel.get("prior_claims", 0) >= 2:
            flags.append("repeat_claimer")
        return {"eligible": True, "amount_inr": min(parcel["declared_value_inr"], DECLARED_VALUE_CAP_INR),
                "flags": flags, "reason": "Damage claim meets policy."}

    # refund_request
    if status == "lost":
        return {"eligible": True, "amount_inr": min(parcel["declared_value_inr"], DECLARED_VALUE_CAP_INR),
                "flags": flags, "reason": "Parcel is lost; declared value is refundable."}
    if status == "delayed" and parcel.get("days_late", 0) > 5:
        return {"eligible": True, "amount_inr": parcel["shipping_fee_inr"], "flags": flags,
                "reason": "Parcel is more than 5 days late; shipping fee is refundable."}
    if status == "delivered":
        return {"eligible": False, "amount_inr": 0, "flags": flags,
                "reason": "We're a courier, so product refunds are handled by the seller."}
    return {"eligible": False, "amount_inr": 0, "flags": flags,
            "reason": "Your parcel is on its way and not yet eligible for a refund."}


def update_address(store: Store, parcel: dict, new_address: str | None) -> dict:
    if parcel["status"] in ("in_transit", "delayed") and new_address:
        store.update_parcel(parcel["tracking_id"], {"delivery_address": new_address})
        return {"updated": True, "new_address": new_address}
    return {"updated": False, "new_address": None}


def create_ticket(store: Store, **doc) -> str:
    return store.create_ticket(doc)
