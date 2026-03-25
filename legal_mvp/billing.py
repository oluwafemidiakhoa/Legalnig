"""Billing tier definitions, usage limits, and subscription helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from legal_mvp.models import BillingRecord, SubscriptionRecord

ALL_TEMPLATES = ["cac_checklist", "employment_contract", "nda", "service_agreement", "shareholders_agreement"]

TIER_DEFINITIONS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "description": "Get started — no credit card required",
        "billing_type": "free",
        "price_ngn": 0,
        "matter_limit": 1,
        "document_limit": 0,
        "qa_monthly_limit": 3,
        "contract_reviews": 0,
        "compliance_alerts": False,
        "allowed_templates": [],
        "features": [
            "1 active matter",
            "Compliance calendar (view only)",
            "3 legal Q&A per month",
            "Document previews (no download)",
            "No credit card required",
        ],
    },
    "professional": {
        "name": "Professional",
        "description": "For growing SMEs that need compliance monitoring",
        "billing_type": "monthly",
        "price_ngn": 25_000,
        "matter_limit": 5,
        "document_limit": 10,
        "qa_monthly_limit": -1,
        "contract_reviews": 3,
        "compliance_alerts": True,
        "allowed_templates": ["cac_checklist", "employment_contract", "nda", "service_agreement"],
        "features": [
            "5 active matters",
            "Email compliance deadline alerts",
            "10 documents per month",
            "3 AI contract reviews per month",
            "Unlimited cited legal Q&A",
            "Employment, NDA & service templates",
        ],
    },
    "scale": {
        "name": "Scale",
        "description": "Unlimited operations + priority lawyer review",
        "billing_type": "monthly",
        "price_ngn": 75_000,
        "matter_limit": -1,
        "document_limit": -1,
        "qa_monthly_limit": -1,
        "contract_reviews": -1,
        "compliance_alerts": True,
        "priority_queue": True,
        "allowed_templates": ALL_TEMPLATES,
        "features": [
            "Unlimited matters & documents",
            "Unlimited AI contract reviews",
            "Priority lawyer review queue",
            "All document templates incl. SHA",
            "Full compliance pack — all sectors",
            "Email + in-app deadline alerts",
        ],
    },
    "law_firm": {
        "name": "Law Firm",
        "description": "Practice management for Nigerian law firms",
        "billing_type": "monthly",
        "price_ngn": 50_000,
        "price_per_seat_ngn": 50_000,
        "matter_limit": -1,
        "document_limit": -1,
        "qa_monthly_limit": -1,
        "contract_reviews": -1,
        "compliance_alerts": True,
        "priority_queue": True,
        "team_management": True,
        "allowed_templates": ALL_TEMPLATES,
        "features": [
            "Everything in Scale",
            "Team seats with role management",
            "Client portal access",
            "Matter assignment to associates",
            "₦50,000 / seat / month",
            "White-label ready",
        ],
    },
    "pay_per_document": {
        "name": "Document (Pay-per-use)",
        "description": "Generate one Nigerian-law document — no subscription needed",
        "billing_type": "one_time",
        "price_ngn": 5_000,
        "matter_limit": 0,
        "document_limit": 1,
        "qa_monthly_limit": 0,
        "contract_reviews": 0,
        "compliance_alerts": False,
        "allowed_templates": ["cac_checklist", "employment_contract", "nda", "service_agreement"],
        "features": [
            "One document: NDA, Employment, Service Agreement or CAC checklist",
            "Lawyer-reviewed template",
            "Instant download",
            "No subscription required",
        ],
    },
    "pay_per_contract_review": {
        "name": "Contract Review (Pay-per-use)",
        "description": "AI risk-flag + lawyer annotation for one contract — no subscription",
        "billing_type": "one_time",
        "price_ngn": 15_000,
        "matter_limit": 0,
        "document_limit": 0,
        "qa_monthly_limit": 0,
        "contract_reviews": 1,
        "compliance_alerts": False,
        "allowed_templates": [],
        "features": [
            "Full AI clause extraction and risk analysis",
            "Lawyer reviews and annotates your contract",
            "Risk flag report (high / medium / low)",
            "No subscription required",
        ],
    },
}

# Tiers that are real subscriptions (not free, not pay-per-use)
SUBSCRIPTION_TIERS = {"professional", "scale", "law_firm"}

# Daily AI call cap per tier (abuse prevention)
DAILY_AI_CAPS = {"free": 3, "professional": 50, "scale": 100, "law_firm": 100}


def get_tier(tier_name: str) -> dict:
    if tier_name not in TIER_DEFINITIONS:
        raise LookupError(f"Tier '{tier_name}' not found.")
    return TIER_DEFINITIONS[tier_name]


def get_user_tier(subscription: dict | None, billing_records: list[dict] | None) -> str:
    """Return the effective tier name for a user right now."""
    if subscription and subscription.get("status") == "active":
        return subscription["tier"]
    # Check pay-per-use credits
    for rec in (billing_records or []):
        if rec.get("status") == "paid" and rec.get("credits_remaining", 0) > 0:
            return rec.get("service_tier", "free")
    return "free"


def check_usage_limit(
    tier_name: str,
    daily_ai_count: int,
    monthly_qa_count: int = 0,
    monthly_doc_count: int = 0,
    monthly_contract_count: int = 0,
) -> tuple[bool, str]:
    """Returns (allowed, reason). reason is '' if allowed."""
    tier = TIER_DEFINITIONS.get(tier_name, TIER_DEFINITIONS["free"])

    daily_cap = DAILY_AI_CAPS.get(tier_name, 3)
    if daily_ai_count >= daily_cap:
        return False, "daily_limit"

    qa_limit = tier.get("qa_monthly_limit", 3)
    if qa_limit != -1 and monthly_qa_count >= qa_limit:
        return False, "qa_monthly_limit"

    doc_limit = tier.get("document_limit", 0)
    if doc_limit == 0:
        return False, "doc_not_included"
    if doc_limit != -1 and monthly_doc_count >= doc_limit:
        return False, "doc_monthly_limit"

    contract_limit = tier.get("contract_reviews", 0)
    if contract_limit == 0:
        return False, "contract_not_included"
    if contract_limit != -1 and monthly_contract_count >= contract_limit:
        return False, "contract_monthly_limit"

    return True, ""


def check_qa_allowed(tier_name: str, daily_count: int, monthly_count: int) -> tuple[bool, str]:
    tier = TIER_DEFINITIONS.get(tier_name, TIER_DEFINITIONS["free"])
    daily_cap = DAILY_AI_CAPS.get(tier_name, 3)
    if daily_count >= daily_cap:
        return False, "daily_limit"
    qa_limit = tier.get("qa_monthly_limit", 3)
    if qa_limit != -1 and monthly_count >= qa_limit:
        return False, "qa_monthly_limit"
    return True, ""


def check_doc_allowed(tier_name: str, monthly_count: int) -> tuple[bool, str]:
    tier = TIER_DEFINITIONS.get(tier_name, TIER_DEFINITIONS["free"])
    doc_limit = tier.get("document_limit", 0)
    if doc_limit == 0:
        return False, "doc_not_included"
    if doc_limit != -1 and monthly_count >= doc_limit:
        return False, "doc_monthly_limit"
    return True, ""


def check_contract_allowed(tier_name: str, monthly_count: int) -> tuple[bool, str]:
    tier = TIER_DEFINITIONS.get(tier_name, TIER_DEFINITIONS["free"])
    limit = tier.get("contract_reviews", 0)
    if limit == 0:
        return False, "contract_not_included"
    if limit != -1 and monthly_count >= limit:
        return False, "contract_monthly_limit"
    return True, ""


def create_billing_record(
    user_id: str,
    tier: str,
    matter_id: str | None = None,
    seat_count: int = 1,
) -> BillingRecord:
    tier_def = get_tier(tier)
    now = datetime.now(timezone.utc)
    is_one_time = tier_def["billing_type"] in ("one_time", "free")
    if is_one_time:
        amount = float(tier_def.get("price_ngn", 0))
        period_start = period_end = None
        description = f"{tier_def['name']} — one-time"
    else:
        per_seat = tier_def.get("price_per_seat_ngn", tier_def.get("price_ngn", 0))
        amount = float(per_seat * seat_count)
        period_start = now.isoformat()
        period_end = (now + timedelta(days=30)).isoformat()
        description = f"{tier_def['name']} — monthly{' ×' + str(seat_count) + ' seats' if seat_count > 1 else ''}"

    return BillingRecord(
        id=str(uuid4()),
        user_id=user_id,
        matter_id=matter_id,
        service_tier=tier,
        billing_type=tier_def["billing_type"],
        amount_ngn=amount,
        status="paid",
        description=description,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        period_start=period_start,
        period_end=period_end,
    )


def create_subscription(user_id: str, tier: str, seat_count: int = 1) -> SubscriptionRecord:
    if tier not in SUBSCRIPTION_TIERS:
        raise ValueError(f"'{tier}' is not a subscription tier.")
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
    tier_name = get_user_tier(subscription, billing_records)
    allowed = TIER_DEFINITIONS.get(tier_name, {}).get("allowed_templates", [])
    return template_key in allowed
