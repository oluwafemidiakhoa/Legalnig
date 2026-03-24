"""AI-powered contract clause extraction and risk flagging. Falls back to regex if no API key."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from legal_mvp.models import ContractReviewRecord

# ── Regex-based clause patterns ────────────────────────────────────────────────

_PATTERNS: dict[str, list[str]] = {
    "governing_law": [
        r"governed by (?:the )?laws? of ([^\n.;,]{3,60})",
        r"subject to (?:the )?laws? of ([^\n.;,]{3,60})",
        r"under (?:the )?laws? of ([^\n.;,]{3,60})",
    ],
    "termination": [
        r"(?:either party|both parties) may terminat[^\n.]{0,120}",
        r"(?:this agreement|contract) (?:shall|may) be terminat[^\n.]{0,120}",
        r"terminat(?:ion|ed) (?:on|upon|with|by) (?:giving|providing)? ?(?:\d+)? ?(?:days?|weeks?|months?)[^\n.]{0,80}",
    ],
    "payment_terms": [
        r"(?:payment|invoice|fee) (?:shall be |is )?(?:due|payable) (?:within|in|on) ([^\n.;]{3,60})",
        r"(\d+) (?:calendar |business )?days? (?:from|after|following) (?:receipt of )?invoice",
    ],
    "ip_assignment": [
        r"(?:all )?(?:intellectual property|IP|inventions?|work product|deliverables?) (?:shall |will )?(?:vest in|belong to|be (?:the )?property of|be assigned to) ([^\n.]{3,60})",
        r"(?:work(?:s?) (?:for hire|made for hire))",
    ],
    "non_compete": [
        r"(?:shall not|must not|agree not to) (?:compete|engage|carry on) [^\n.]{0,60}(?:for|during) (\d+ (?:months?|years?))[^\n.]{0,60}",
        r"non[- ]competi(?:tion|tive) (?:covenant|clause|period|restriction)[^\n.]{0,120}",
    ],
    "dispute_resolution": [
        r"(?:disputes?|controversies?|differences?) (?:shall|will|must) (?:be )?(?:resolved|settled|referred|submitted) (?:to|by|through|via) ([^\n.;]{3,80})",
        r"(?:arbitration|mediation|litigation) (?:under|pursuant to|in accordance with|at) ([^\n.;]{3,60})",
    ],
    "liability_cap": [
        r"(?:total |aggregate )?liability (?:of (?:either|each) party )?(?:shall not exceed|is limited to|shall be limited to) ([^\n.;]{3,60})",
        r"in no event shall [^\n.]{0,60}(?:exceed|be liable for more than) ([^\n.;]{3,60})",
    ],
    "confidentiality": [
        r"confidential(?:ity)? (?:information|obligations?|clause)[^\n.]{0,120}",
        r"(?:shall|will|must) (?:keep|maintain|hold|treat) [^\n.]{0,40}(?:confidential|secret|proprietary)[^\n.]{0,80}",
    ],
}

# ── Risk flag rules ────────────────────────────────────────────────────────────

_RISK_FLAGS = [
    {
        "id": "non_nigerian_governing_law",
        "severity": "high",
        "description": "Governing law is not Nigerian law. Nigerian courts may decline to enforce certain clauses, and enforcement against Nigerian assets could be complex.",
        "check_key": "governing_law",
        "check_fn": lambda text: text and "nigeria" not in text.lower(),
    },
    {
        "id": "broad_ip_assignment",
        "severity": "high",
        "description": "IP assignment clause appears broad. Ensure pre-existing IP ('Background IP') is carved out and the counterparty is not obtaining rights to work created before this contract.",
        "check_key": "ip_assignment",
        "check_fn": lambda text: bool(text),
    },
    {
        "id": "no_dispute_resolution",
        "severity": "medium",
        "description": "No clear dispute resolution mechanism found. Without this, disputes default to full court litigation — consider adding an arbitration or mediation clause.",
        "check_key": "dispute_resolution",
        "check_fn": lambda text: not text,
    },
    {
        "id": "no_payment_terms",
        "severity": "medium",
        "description": "No explicit payment terms found. Ambiguous payment timing creates cash flow risk.",
        "check_key": "payment_terms",
        "check_fn": lambda text: not text,
    },
    {
        "id": "no_confidentiality",
        "severity": "medium",
        "description": "No confidentiality clause detected. Shared business information may not be protected.",
        "check_key": "confidentiality",
        "check_fn": lambda text: not text,
    },
    {
        "id": "broad_non_compete",
        "severity": "medium",
        "description": "Non-compete restriction found. Under Nigerian law, non-competes exceeding 12 months or with overly broad geographic scope may be unenforceable as a restraint of trade.",
        "check_key": "non_compete",
        "check_fn": lambda text: bool(text),
    },
    {
        "id": "no_termination_clause",
        "severity": "medium",
        "description": "No termination clause detected. Without this, either party may find it difficult to exit the agreement.",
        "check_key": "termination",
        "check_fn": lambda text: not text,
    },
    {
        "id": "no_liability_cap",
        "severity": "low",
        "description": "No liability cap found. Consider capping liability to the value of fees paid under the contract.",
        "check_key": "liability_cap",
        "check_fn": lambda text: not text,
    },
]


def extract_clauses_regex(text: str) -> dict[str, str]:
    """Extract key clauses using regex patterns. Returns dict of clause_key → extracted text."""
    results: dict[str, str] = {}
    normalised = " ".join(text.split())
    for clause_key, patterns in _PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalised, re.IGNORECASE)
            if match:
                results[clause_key] = match.group(0).strip()[:300]
                break
    return results


def flag_risks(extracted_clauses: dict[str, str]) -> list[dict]:
    """Apply risk rules to extracted clauses. Returns list of risk flag dicts."""
    flags = []
    for rule in _RISK_FLAGS:
        clause_text = extracted_clauses.get(rule["check_key"], "")
        if rule["check_fn"](clause_text):
            flags.append({
                "id": rule["id"],
                "severity": rule["severity"],
                "description": rule["description"],
                "clause_ref": rule["check_key"],
                "extracted_text": clause_text or None,
            })
    return flags


def _build_ai_prompt(filename: str, raw_text: str, extracted_clauses: dict) -> str:
    snippet = raw_text[:3000]
    clauses_json = json.dumps(extracted_clauses, indent=2)
    return (
        f"You are a Nigerian contract review specialist. Review the following contract excerpt "
        f"from '{filename}' and provide a structured analysis.\n\n"
        f"REGEX PRE-EXTRACTION (may be incomplete):\n{clauses_json}\n\n"
        f"CONTRACT TEXT:\n{snippet}\n\n"
        f"Return a JSON object with these keys:\n"
        f"- parties: list of party names\n"
        f"- governing_law: string (country/state)\n"
        f"- termination_clauses: list of termination trigger descriptions\n"
        f"- payment_terms: string summary\n"
        f"- ip_assignment: string (who owns IP, any carve-outs)\n"
        f"- non_compete: string (duration, scope) or null\n"
        f"- dispute_resolution: string (mechanism, seat)\n"
        f"- liability_cap: string or null\n"
        f"- confidentiality: string summary or null\n"
        f"- summary: 2-3 sentence plain-English summary for a Nigerian SME founder\n"
        f"- additional_risks: list of strings describing any other Nigerian-law-specific risks\n"
        f"\nReturn ONLY valid JSON."
    )


def _call_openai_json(prompt: str) -> dict | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("OPENAI_ANSWER_MODEL", "gpt-4o-mini")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return None


def run_ai_contract_review(record: dict) -> dict:
    """
    Run AI contract review on a contract review record dict.
    Updates extracted_clauses, risk_flags, ai_summary, and status.
    Returns the updated record dict.
    """
    raw_text = record.get("raw_text", "")
    filename = record.get("filename", "contract.txt")

    # Start with regex extraction
    extracted = extract_clauses_regex(raw_text)

    # Attempt AI enrichment
    ai_result = _call_openai_json(_build_ai_prompt(filename, raw_text, extracted))
    if ai_result:
        for key in ("governing_law", "payment_terms", "ip_assignment", "non_compete",
                    "dispute_resolution", "liability_cap", "confidentiality"):
            if ai_result.get(key):
                extracted[key] = str(ai_result[key])[:300]
        summary = ai_result.get("summary", "")
        additional = ai_result.get("additional_risks", [])
    else:
        summary = _build_fallback_summary(extracted, filename)
        additional = []

    risks = flag_risks(extracted)
    for extra in additional:
        risks.append({"id": "ai_flag", "severity": "medium", "description": str(extra)[:300], "clause_ref": None, "extracted_text": None})

    now = datetime.now(timezone.utc).isoformat()
    record["extracted_clauses"] = extracted
    record["risk_flags"] = risks
    record["ai_summary"] = summary
    record["status"] = "ai_reviewed"
    record["updated_at"] = now
    return record


def _build_fallback_summary(extracted: dict, filename: str) -> str:
    parts = [f"Contract review of '{filename}' (regex analysis — AI enrichment unavailable)."]
    if extracted.get("governing_law"):
        parts.append(f"Governing law: {extracted['governing_law'][:80]}.")
    if extracted.get("payment_terms"):
        parts.append(f"Payment terms: {extracted['payment_terms'][:80]}.")
    if not extracted.get("dispute_resolution"):
        parts.append("No dispute resolution clause detected.")
    parts.append("A licensed Nigerian lawyer should review before execution.")
    return " ".join(parts)


def create_contract_review(
    matter_id: str,
    submitted_by_user_id: str,
    filename: str,
    raw_text: str,
) -> ContractReviewRecord:
    now = datetime.now(timezone.utc).isoformat()
    return ContractReviewRecord(
        id=str(uuid4()),
        matter_id=matter_id,
        submitted_by_user_id=submitted_by_user_id,
        filename=filename,
        raw_text=raw_text,
        status="pending_ai_review",
        ai_summary="",
        extracted_clauses={},
        risk_flags=[],
        lawyer_annotations=[],
        created_at=now,
        updated_at=now,
    )
