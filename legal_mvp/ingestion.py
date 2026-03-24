from __future__ import annotations

import hashlib

from legal_mvp.models import SourceDocument


def build_source_document(payload: dict) -> SourceDocument:
    required_fields = (
        "source_key",
        "title",
        "issuer",
        "jurisdiction",
        "area",
        "citation_label",
        "body_text",
    )
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"Missing source document fields: {', '.join(missing)}")

    values = {}
    for field in required_fields:
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        values[field] = value.strip()

    canonical_url = payload.get("canonical_url")
    if canonical_url is not None:
        if not isinstance(canonical_url, str):
            raise ValueError("canonical_url must be a string when provided.")
        canonical_url = canonical_url.strip() or None

    return SourceDocument(
        source_key=values["source_key"],
        title=values["title"],
        issuer=values["issuer"],
        jurisdiction=values["jurisdiction"],
        area=values["area"],
        citation_label=values["citation_label"],
        body_text=values["body_text"],
        canonical_url=canonical_url,
        production_ready=bool(payload.get("production_ready", False)),
    )


def chunk_text(text: str, max_words: int = 110, overlap_words: int = 18) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(end - overlap_words, start + 1)
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
