from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from legal_mvp.jurisdictions import DEFAULT_JURISDICTION, get_jurisdiction_pack, normalize_jurisdiction
from legal_mvp.runtime_env import load_env_file


load_env_file()

DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_ANSWER_MODEL = os.getenv("OPENAI_ANSWER_MODEL", "gpt-5-mini")
ANSWER_DISCLAIMER = (
    "Draft operational guidance only. A licensed lawyer should review this answer before client use."
)

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "answer_status",
        "answer_text",
        "risk_level",
        "requires_lawyer_review",
        "recommended_actions",
        "follow_up_questions",
        "citation_ids",
    ],
    "properties": {
        "answer_status": {
            "type": "string",
            "enum": ["supported", "insufficient_sources"],
        },
        "answer_text": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "requires_lawyer_review": {"type": "boolean"},
        "recommended_actions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "follow_up_questions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "citation_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def prepare_citation_context(citations: list[dict[str, object]]) -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    for index, citation in enumerate(citations, start=1):
        prepared.append(
            {
                "source_id": f"SRC-{index}",
                "title": citation["title"],
                "issuer": citation["issuer"],
                "area": citation["area"],
                "jurisdiction": citation["jurisdiction"],
                "citation_label": citation["citation_label"],
                "snippet": citation["snippet"],
                "canonical_url": citation.get("canonical_url"),
            }
        )
    return prepared


def generate_answer_draft(
    question: str,
    citations: list[dict[str, object]],
    jurisdiction: str | None = None,
) -> dict[str, object]:
    question = question.strip()
    if not question:
        raise ValueError("question must be a non-empty string.")

    active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
    prepared_citations = prepare_citation_context(citations)
    if not prepared_citations:
        return build_insufficient_answer(
            question,
            "No supporting citations were retrieved.",
            [],
            DEFAULT_ANSWER_MODEL,
            active_jurisdiction,
        )

    response_payload = request_structured_answer(question, prepared_citations, active_jurisdiction)
    response_text = extract_response_output_text(response_payload)
    parsed = json.loads(response_text)
    normalized = normalize_answer_payload(parsed, prepared_citations)
    return build_answer_draft(question, normalized, DEFAULT_ANSWER_MODEL, active_jurisdiction)


def request_structured_answer(
    question: str,
    citations: list[dict[str, object]],
    jurisdiction: str | None = None,
) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for legal answer generation.")

    pack = get_jurisdiction_pack(jurisdiction)
    prompt = build_user_prompt(question, citations)
    payload = {
        "model": DEFAULT_ANSWER_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    f"You are the {pack.assistant_name}, drafting operational legal guidance for internal review. "
                    "Use only the provided source excerpts. If the excerpts do not support a claim, mark "
                    "the answer as insufficient_sources. Do not claim to be a lawyer and do not provide "
                    "final legal advice. Keep the answer concise, practical, and explicit about lawyer review."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "legal_answer",
                "strict": True,
                "schema": ANSWER_SCHEMA,
            }
        },
    }

    request = urllib.request.Request(
        f"{DEFAULT_OPENAI_BASE_URL}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - network runtime path
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI answer request failed: {details}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network runtime path
        raise RuntimeError(f"OpenAI answer request failed: {exc}") from exc


def build_user_prompt(question: str, citations: list[dict[str, object]]) -> str:
    lines = [
        "Question:",
        question,
        "",
        "Available source excerpts:",
    ]
    for item in citations:
        lines.extend(
            [
                f"{item['source_id']} | {item['citation_label']} | {item['title']}",
                f"Jurisdiction: {item['jurisdiction']} | Area: {item['area']} | Issuer: {item['issuer']}",
                f"Excerpt: {item['snippet']}",
                "",
            ]
        )
    lines.extend(
        [
            "Use citation_ids only from the listed SRC identifiers.",
            "If the excerpts are not enough, set answer_status to insufficient_sources.",
        ]
    )
    return "\n".join(lines)


def extract_response_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    outputs = payload.get("output", [])
    fragments: list[str] = []
    for item in outputs:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text") or content.get("value")
                if isinstance(text, str) and text.strip():
                    fragments.append(text)
    if fragments:
        return "".join(fragments)
    raise RuntimeError("OpenAI answer response did not include output text.")


def normalize_answer_payload(payload: dict, citations: list[dict[str, object]]) -> dict[str, object]:
    source_map = {item["source_id"]: item for item in citations}
    valid_ids = [source_id for source_id in payload.get("citation_ids", []) if source_id in source_map]

    answer_status = payload.get("answer_status", "insufficient_sources")
    if answer_status == "supported" and not valid_ids:
        answer_status = "insufficient_sources"

    return {
        "answer_status": answer_status,
        "answer_text": str(payload.get("answer_text", "")).strip(),
        "risk_level": payload.get("risk_level", "high"),
        "requires_lawyer_review": bool(payload.get("requires_lawyer_review", True)),
        "recommended_actions": [str(item).strip() for item in payload.get("recommended_actions", []) if str(item).strip()],
        "follow_up_questions": [str(item).strip() for item in payload.get("follow_up_questions", []) if str(item).strip()],
        "citations": [source_map[source_id] for source_id in valid_ids],
    }


def build_answer_draft(
    question: str,
    payload: dict[str, object],
    model: str,
    jurisdiction: str | None = None,
) -> dict[str, object]:
    requires_review = bool(payload["requires_lawyer_review"]) or payload["risk_level"] == "high"
    active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
    pack = get_jurisdiction_pack(active_jurisdiction)
    return {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": active_jurisdiction,
        "question": question,
        "status": payload["answer_status"],
        "answer_text": payload["answer_text"],
        "risk_level": payload["risk_level"],
        "requires_lawyer_review": requires_review,
        "recommended_actions": payload["recommended_actions"][:5],
        "follow_up_questions": payload["follow_up_questions"][:5],
        "citations": payload["citations"],
        "model": model,
        "review_status": "pending_lawyer_review" if requires_review else "draft_ready",
        "reviewer_name": None,
        "review_notes": None,
        "reviewed_at": None,
        "disclaimer": (
            f"Draft operational guidance only. A {pack.lawyer_label} should review this answer before client use."
        ),
    }


def build_insufficient_answer(
    question: str,
    reason: str,
    citations: list[dict[str, object]],
    model: str,
    jurisdiction: str | None = None,
) -> dict[str, object]:
    active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
    pack = get_jurisdiction_pack(active_jurisdiction)
    return {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jurisdiction": active_jurisdiction,
        "question": question,
        "status": "insufficient_sources",
        "answer_text": reason,
        "risk_level": "high",
        "requires_lawyer_review": True,
        "recommended_actions": [
            f"Add more counsel-approved {active_jurisdiction} source documents for this topic.",
            f"Escalate the matter to a {pack.lawyer_label} before any client-facing use.",
        ],
        "follow_up_questions": [],
        "citations": citations,
        "model": model,
        "review_status": "pending_lawyer_review",
        "reviewer_name": None,
        "review_notes": None,
        "reviewed_at": None,
        "disclaimer": (
            f"Draft operational guidance only. A {pack.lawyer_label} should review this answer before client use."
        ),
    }
