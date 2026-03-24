from __future__ import annotations

from legal_mvp.jurisdictions import DEFAULT_JURISDICTION, normalize_jurisdiction
from legal_mvp.models import LegalSource


BASE_SOURCES = [
    LegalSource(
        title="Companies and Allied Matters Act (CAMA) source pack",
        issuer="Counsel-curated statutory registry",
        jurisdiction="Nigeria",
        area="company formation",
        usage_note="Attach section-level citations before production answers.",
    ),
    LegalSource(
        title="Corporate Affairs Commission (CAC) filing guidance pack",
        issuer="Operations and counsel review",
        jurisdiction="Nigeria",
        area="company formation",
        usage_note="Use for workflow steps, forms, and filing checkpoints.",
    ),
    LegalSource(
        title="Federal Inland Revenue Service (FIRS) tax onboarding guidance pack",
        issuer="Tax counsel review",
        jurisdiction="Nigeria",
        area="tax onboarding",
        usage_note="Confirm current registration and reporting obligations before use.",
    ),
    LegalSource(
        title="Employment and workplace policy source pack",
        issuer="Labour counsel review",
        jurisdiction="Nigeria",
        area="employment",
        usage_note="Use only after clause review and issue spotting.",
    ),
    LegalSource(
        title="Nigeria data protection and privacy source pack",
        issuer="Privacy counsel review",
        jurisdiction="Nigeria",
        area="data protection",
        usage_note="Map customer data collection and consent obligations before launch.",
    ),
    LegalSource(
        title="Nigeria sector licensing issue list",
        issuer="Regulatory counsel review",
        jurisdiction="Nigeria",
        area="regulated sectors",
        usage_note="Required for fintech, health, education, logistics, and sector-specific filings.",
    ),
]


def select_sources(entity_type: str, sector: str, use_case: str, jurisdiction: str | None = None) -> list[LegalSource]:
    selected: list[LegalSource] = []
    active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
    sector_normalized = sector.strip().lower()
    use_case_normalized = use_case.strip().lower()
    available_sources = [source for source in BASE_SOURCES if source.jurisdiction == active_jurisdiction]

    for source in available_sources[:3]:
        selected.append(source)

    if "employee" in use_case_normalized or "employment" in use_case_normalized:
        selected.append(available_sources[3])

    if any(keyword in use_case_normalized for keyword in ("privacy", "data", "portal", "saas")):
        selected.append(available_sources[4])

    if sector_normalized in {"fintech", "health", "education", "logistics", "energy"}:
        selected.append(available_sources[5])

    # Preserve order while removing duplicates.
    deduped: list[LegalSource] = []
    seen: set[tuple[str, str]] = set()
    for source in selected:
        key = (source.title, source.area)
        if key not in seen:
            seen.add(key)
            deduped.append(source)
    return deduped
