"""Billing tier definitions and subscription helpers. No external dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from legal_mvp.models import BillingRecord, SubscriptionRecord

TIER_DEFINITIONS: dict[str, dict] = {
    "starter": {
        "name": "Starter",
        "description": "Single business setup — one-time engagement",
        "billing_type": "one_time",
        "price_ngn": 150_000,
        "features": [
            "CAC pre-incorporation checklist",
            "Business name availability guidance",
            "TIN registration checklist",
            "1 matter packet",
            "Basic source-backed Q&A",
        ],
        "document_limit": 2,
        "matter_limit": 1,
        "contract_reviews": 0,
        "allowed_templates": ["cac_checklist"],
    },
    "growth": {
        "name": "Growth",
        "description": "Recurring compliance monitoring for growing SMEs",
        "billing_type": "monthly",
        "price_ngn": 50_000,
        "features": [
            "Compliance calendar with deadline alerts",
            "VAT / PAYE / PENCOM reminders",
            "Up to 5 active matters",
            "Employment & NDA templates",
            "Service agreement template",
            "Unlimited cited legal Q&A",
        ],
        "document_limit": 10,
        "matter_limit": 5,
        "contract_reviews": 2,
        "allowed_templates": ["cac_checklist", "employment_contract", "nda", "service_agreement"],
    },
    "scale": {
        "name": "Scale",
        "description": "Unlimited documents, contract review, and priority lawyer queue",
        "billing_type": "monthly",
        "price_ngn": 150_000,
        "features": [
            "Everything in Growth",
            "Unlimited matters and documents",
            "AI contract review (unlimited uploads)",
            "Shareholders agreement template",
            "Priority lawyer review queue",
            "Compliance pack: all sectors",
        ],
        "document_limit": -1,
        "matter_limit": -1,
        "contract_reviews": -1,
        "allowed_templates": ["cac_checklist", "employment_contract", "nda", "service_agreement", "shareholders_agreement"],
    },
    "law_firm": {
        "name": "Law Firm",
        "description": "Practice management software licence for law firms — per seat",
        "billing_type": "monthly",
        "price_ngn": 75_000,
        "price_per_seat_ngn": 75_000,
        "features": [
            "Everything in Scale",
            "Multi-user team with role assignments",
            "Client portal access",
            "Matter assignment to associates",
            "Time tracking stubs",
            "Template library management",
            "White-label ready",
        ],
        "document_limit": -1,
        "matter_limit": -1,
        "contract_reviews": -1,
        "allowed_templates": ["cac_checklist", "employment_contract", "nda", "service_agreement", "shareholders_agreement"],
    },
}


def get_tier(tier_name: str) -> dict:
    if tier_name not in TIER_DEFINITIONS:
        raise LookupError(f"Tier '{tier_name}' not found.")
    return TIER_DEFINITIONS[tier_name]


def create_billing_record(
    user_id: str,
    tier: str,
    matter_id: str | None = None,
    seat_count: int = 1,
) -> BillingRecord:
    tier_def = get_tier(tier)
    now = datetime.now(timezone.utc)
    if tier_def["billing_type"] == "one_time":
        amount = float(tier_def["price_ngn"])
        period_start = None
        period_end = None
        description = f"{tier_def['name']} — one-time business setup"
    else:
        per_seat = tier_def.get("price_per_seat_ngn", tier_def.get("price_ngn", 0))
        amount = float(per_seat * seat_count)
        period_start = now.isoformat()
        period_end = (now + timedelta(days=30)).isoformat()
        description = f"{tier_def['name']} — monthly subscription{' ×' + str(seat_count) + ' seats' if seat_count > 1 else ''}"

    return BillingRecord(
        id=str(uuid4()),
        user_id=user_id,
        matter_id=matter_id,
        service_tier=tier,
        billing_type=tier_def["billing_type"],
        amount_ngn=amount,
        status="active" if tier_def["billing_type"] == "one_time" else "pending",
        description=description,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        period_start=period_start,
        period_end=period_end,
    )


def create_subscription(
    user_id: str,
    tier: str,
    seat_count: int = 1,
) -> SubscriptionRecord:
    tier_def = get_tier(tier)
    if tier_def["billing_type"] == "one_time":
        raise ValueError(f"Tier '{tier}' is a one-time purchase and cannot be subscribed.")
    now = datetime.now(timezone.utc)
    return SubscriptionRecord(
        id=str(uuid4()),
        user_id=user_id,
        tier=tier,
        seat_count=seat_count,
        status="active",
        started_at=now.isoformat(),
        next_billing_at=(now + timedelta(days=30)).isoformat(),
        created_at=now.isoformat(),
    )


def check_feature_access(
    template_key: str,
    subscription: dict | None,
    billing_records: list[dict] | None = None,
) -> bool:
    """Return True if the user can access this template given their subscription/billing."""
    # Check active subscriptions
    if subscription and subscription.get("status") == "active":
        tier_def = TIER_DEFINITIONS.get(subscription.get("tier", ""), {})
        allowed = tier_def.get("allowed_templates", [])
        if template_key in allowed:
            return True

    # Check one-time billing records
    for record in (billing_records or []):
        if record.get("status") in ("active", "completed"):
            tier_def = TIER_DEFINITIONS.get(record.get("service_tier", ""), {})
            allowed = tier_def.get("allowed_templates", [])
            if template_key in allowed:
                return True

    return False
