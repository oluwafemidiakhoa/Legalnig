from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class IntakeRequest:
    jurisdiction: str
    founder_name: str
    business_name: str
    entity_type: str
    sector: str
    use_case: str
    contact_email: str
    consent: bool
    # Optional extended fields
    shareholders: list = field(default_factory=list)
    estimated_employees: str = "0"
    phone_number: str | None = None
    state_of_registration: str | None = None
    existing_registrations: list = field(default_factory=list)
    incorporation_date: str | None = None


@dataclass
class WorkflowStep:
    title: str
    owner: str
    rationale: str
    risk_level: str


@dataclass
class DocumentBrief:
    title: str
    purpose: str
    sections: list[str]
    review_required: bool = True


@dataclass
class LegalSource:
    title: str
    issuer: str
    jurisdiction: str
    area: str
    usage_note: str
    production_ready: bool = False


@dataclass
class SourceDocument:
    source_key: str
    title: str
    issuer: str
    jurisdiction: str
    area: str
    citation_label: str
    body_text: str
    canonical_url: str | None = None
    production_ready: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IntakeRecord:
    id: str
    matter_id: str
    submitted_at: str
    jurisdiction: str
    founder_name: str
    business_name: str
    entity_type: str
    sector: str
    use_case: str
    contact_email: str
    consent: bool
    status: str
    workflow: list[WorkflowStep]
    documents: list[DocumentBrief]
    sources: list[LegalSource]
    disclaimers: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Extended fields on IntakeRequest ──────────────────────────────────────────

@dataclass
class ShareholderEntry:
    name: str
    email: str
    ownership_pct: float


@dataclass
class MatterTask:
    id: str
    matter_id: str
    source_record_id: str | None
    title: str
    owner: str
    status: str
    risk_level: str
    rationale: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ApprovalRecord:
    id: str
    matter_id: str
    artifact_type: str
    artifact_id: str
    title: str
    status: str
    requested_role: str
    requested_at: str
    reviewer_name: str | None = None
    notes: str | None = None
    decided_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocumentVersion:
    id: str
    matter_id: str
    title: str
    document_type: str
    source_record_id: str
    version_number: int
    status: str
    summary: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatterRecord:
    id: str
    created_at: str
    updated_at: str
    title: str
    client_name: str
    contact_email: str
    jurisdiction: str
    sector: str
    matter_type: str
    status: str
    source_record_type: str
    source_record_id: str | None
    summary: str
    tasks: list[MatterTask]
    approvals: list[ApprovalRecord]
    document_versions: list[DocumentVersion]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Auth ───────────────────────────────────────────────────────────────────────

@dataclass
class UserRecord:
    id: str
    email: str
    display_name: str
    role: str                   # sme_founder | lawyer | admin
    password_hash: str
    salt: str
    is_active: bool
    created_at: str
    matter_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionToken:
    token: str
    user_id: str
    role: str
    expires_at: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── Billing ────────────────────────────────────────────────────────────────────

@dataclass
class BillingRecord:
    id: str
    user_id: str
    service_tier: str           # starter | growth | scale | law_firm
    billing_type: str           # one_time | monthly
    amount_ngn: float
    status: str                 # pending | active | cancelled | expired
    description: str
    created_at: str
    updated_at: str
    matter_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubscriptionRecord:
    id: str
    user_id: str
    tier: str                   # growth | scale | law_firm
    seat_count: int
    status: str                 # active | cancelled | expired
    started_at: str
    created_at: str
    next_billing_at: str | None = None
    cancelled_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ── Compliance calendar ────────────────────────────────────────────────────────

@dataclass
class ComplianceObligation:
    id: str
    matter_id: str
    obligation_type: str
    description: str
    due_date: str               # ISO date
    status: str                 # upcoming | due_soon | overdue | completed | waived
    recurrence: str             # one_time | monthly | annual | biennial
    alert_sent: bool
    created_at: str
    updated_at: str
    completed_at: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ── Contract review ────────────────────────────────────────────────────────────

@dataclass
class ContractReviewRecord:
    id: str
    matter_id: str
    submitted_by_user_id: str
    filename: str
    raw_text: str
    status: str                 # pending_ai_review | ai_reviewed | lawyer_annotating | lawyer_approved | rejected
    ai_summary: str
    created_at: str
    updated_at: str
    extracted_clauses: dict = field(default_factory=dict)
    risk_flags: list = field(default_factory=list)
    lawyer_annotations: list = field(default_factory=list)
    assigned_lawyer_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ── Generated documents ────────────────────────────────────────────────────────

@dataclass
class GeneratedDocument:
    id: str
    matter_id: str
    template_key: str
    title: str
    body_text: str
    status: str                 # draft | pending_review | approved | rejected
    generated_at: str
    version_number: int
    approved_by_user_id: str | None = None
    approved_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
