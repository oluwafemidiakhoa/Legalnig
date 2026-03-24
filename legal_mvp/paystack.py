"""Paystack payment integration — stdlib only (urllib.request)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from uuid import uuid4

BASE_URL   = "https://api.paystack.co"
SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
ENABLED    = bool(SECRET_KEY)


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url  = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {SECRET_KEY}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def initialize_transaction(
    email: str,
    amount_ngn: float,
    tier: str,
    user_id: str,
    callback_url: str = "http://127.0.0.1:8000/api/billing/verify",
) -> dict:
    """
    Returns Paystack authorization_url, access_code, reference.
    amount_ngn is in Naira — converted to kobo internally.
    """
    if not ENABLED:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")
    reference = f"FL-{tier[:3].upper()}-{uuid4().hex[:10].upper()}"
    payload = {
        "email": email,
        "amount": int(amount_ngn * 100),   # kobo
        "currency": "NGN",
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {"tier": tier, "user_id": user_id},
    }
    result = _request("POST", "/transaction/initialize", payload)
    if not result.get("status"):
        raise ValueError(result.get("message", "Paystack initialization failed."))
    return result["data"]  # keys: authorization_url, access_code, reference


def verify_transaction(reference: str) -> dict:
    """
    Verify a completed transaction.
    Returns data dict; raises ValueError if payment not successful.
    """
    if not ENABLED:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")
    result = _request("GET", f"/transaction/verify/{reference}")
    if not result.get("status"):
        raise ValueError(result.get("message", "Verification failed."))
    data = result["data"]
    if data.get("status") != "success":
        raise ValueError(f"Payment not completed. Status: {data.get('status')}")
    return data


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Validate x-paystack-signature header using HMAC-SHA512."""
    if not SECRET_KEY:
        return False
    computed = hmac.new(
        SECRET_KEY.encode(),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(computed, signature_header or "")
