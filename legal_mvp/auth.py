"""Token-based authentication and role enforcement. No external dependencies."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from legal_mvp.models import SessionToken, UserRecord

VALID_ROLES = {"sme_founder", "lawyer", "admin"}
SESSION_TTL_HOURS = 24


# ── Password helpers ───────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    key = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def create_user(email: str, display_name: str, role: str, password: str) -> UserRecord:
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of: {', '.join(sorted(VALID_ROLES))}")
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters.")
    salt = secrets.token_hex(16)
    return UserRecord(
        id=str(uuid4()),
        email=email.lower().strip(),
        display_name=display_name.strip(),
        role=role,
        password_hash=_hash_password(password, salt),
        salt=salt,
        is_active=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        matter_ids=[],
    )


def verify_password(user_record: dict, password: str) -> bool:
    expected = _hash_password(password, user_record["salt"])
    return hmac.compare_digest(expected, user_record["password_hash"])


# ── Session management ─────────────────────────────────────────────────────────

def create_session(user_record: dict) -> SessionToken:
    now = datetime.now(timezone.utc)
    return SessionToken(
        token=secrets.token_hex(32),
        user_id=user_record["id"],
        role=user_record["role"],
        expires_at=(now + timedelta(hours=SESSION_TTL_HOURS)).isoformat(),
        created_at=now.isoformat(),
    )


def is_session_valid(session: dict) -> bool:
    try:
        expires_at = session["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires_at
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


# ── Request helper ─────────────────────────────────────────────────────────────

def extract_bearer_token(authorization_header: str) -> str | None:
    """Parse 'Bearer <token>' from Authorization header. Returns raw token or None."""
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return None


def safe_user_dict(user_record: dict) -> dict:
    """Return user dict with sensitive fields stripped."""
    return {
        "id": user_record["id"],
        "email": user_record["email"],
        "display_name": user_record["display_name"],
        "role": user_record["role"],
        "is_active": user_record.get("is_active", True),
        "created_at": user_record["created_at"],
    }
