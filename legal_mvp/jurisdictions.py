from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JurisdictionPack:
    code: str
    name: str
    app_title: str
    lawyer_label: str
    assistant_name: str


NIGERIA = JurisdictionPack(
    code="NG",
    name="Nigeria",
    app_title="AI Law Firm OS for Nigeria",
    lawyer_label="licensed Nigerian lawyer",
    assistant_name="Nigeria legal operations assistant",
)

DEFAULT_JURISDICTION = NIGERIA.name

_ALIASES = {
    "ng": NIGERIA.name,
    "nigeria": NIGERIA.name,
}


def normalize_jurisdiction(value: str | None) -> str:
    if value is None:
        return DEFAULT_JURISDICTION
    normalized = value.strip().lower()
    if not normalized:
        return DEFAULT_JURISDICTION
    if normalized in _ALIASES:
        return _ALIASES[normalized]
    raise ValueError("Unsupported jurisdiction. Start with Nigeria.")


def get_jurisdiction_pack(value: str | None = None) -> JurisdictionPack:
    jurisdiction = normalize_jurisdiction(value)
    if jurisdiction == NIGERIA.name:
        return NIGERIA
    raise ValueError("Unsupported jurisdiction. Start with Nigeria.")
