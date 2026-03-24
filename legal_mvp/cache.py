"""Answer cache — stdlib only. sha256-keyed, 7-day TTL."""
from __future__ import annotations
import hashlib
from datetime import datetime, timedelta, timezone

CACHE_TTL_DAYS = 7


def question_hash(question: str, jurisdiction: str) -> str:
    normalized = f"{jurisdiction.lower().strip()}::{question.lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def is_cache_fresh(created_at: str | datetime, ttl_days: int = CACHE_TTL_DAYS) -> bool:
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created_at < timedelta(days=ttl_days)
