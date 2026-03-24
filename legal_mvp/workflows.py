from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from legal_mvp.jurisdictions import get_jurisdiction_pack, normalize_jurisdiction
from legal_mvp.models import DocumentBrief, IntakeRecord, IntakeRequest, WorkflowStep
from legal_mvp.sources import select_sources


REGULATED_SECTORS = {"fintech", "health", "education", "logistics", "energy"}
HIGH_RISK_SECTORS = {"fintech", "health"}  # require CBN/NAFDAC pre-launch counsel


def build_disclaimers(jurisdiction: str) -> list[str]:
    pack = get_jurisdiction_pack(jurisdiction)
    return [
        "This system generates draft legal operations packets, not legal advice.",
        f"A {pack.lawyer_label} should review all filings, contract language, and formal guidance before use.",
        "Production answers should include citations to counsel-approved source materials.",
    ]


def build_intake_request(payload: dict) -> IntakeRequest:
    required_fields = (
        "founder_name",
        "business_name",
        "entity_type",
        "sector",
        "use_case",
        "contact_email",
        "consent",
    )
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    consent = bool(payload["consent"])
    if not consent:
        raise ValueError("Consent is required before creating a legal workflow packet.")

    values = {"jurisdiction": normalize_jurisdiction(payload.get("jurisdiction"))}
    for field in required_fields:
        value = payload[field]
        if field == "consent":
            values[field] = consent
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        values[field] = value.strip()

    # Optional extended fields
    values["shareholders"] = payload.get("shareholders") or []
    values["estimated_employees"] = payload.get("estimated_employees") or "0"
    values["phone_number"] = payload.get("phone_number") or None
    values["state_of_registration"] = payload.get("state_of_registration") or "Lagos"
    values["existing_registrations"] = payload.get("existing_registrations") or []
    values["incorporation_date"] = payload.get("incorporation_date") or None

    return IntakeRequest(**values)


# ── CAC Registration workflow steps ───────────────────────────────────────────

CAC_WORKFLOW_STEPS = [
    WorkflowStep(
        title="Run company name availability search on CAC portal",
        owner="assistant",
        rationale="Name reservation (valid 60 days) must precede all other formation steps. Search at pre-rc.cac.gov.ng.",
        risk_level="low",
    ),
    WorkflowStep(
        title="Collect full particulars for all founders and directors",
        owner="legal_ops",
        rationale="CAC requires NIN/passport, address, occupation, and passport photo for each director and shareholder.",
        risk_level="medium",
    ),
    WorkflowStep(
        title="Draft and review Memorandum and Articles of Association (MEMART)",
        owner="lawyer",
        rationale="The objects clause, share structure, and director powers require counsel review before CAC submission (CAMA 2020 s.27).",
        risk_level="high",
    ),
    WorkflowStep(
        title="File pre-incorporation forms and MEMART on CAC portal",
        owner="legal_ops",
        rationale="Submit via pre-rc.cac.gov.ng or accredited CAC agent. Pay prescribed filing fees.",
        risk_level="medium",
    ),
    WorkflowStep(
        title="Collect Certificate of Incorporation and certified MEMART copy",
        owner="legal_ops",
        rationale="The CI and CTC of MEMART are required for bank account opening and all subsequent regulatory filings.",
        risk_level="low",
    ),
    WorkflowStep(
        title="Register for TIN with FIRS (within 6 months of CI)",
        owner="legal_ops",
        rationale="TIN is required for bank accounts, government contracts, and VAT/CIT/WHT compliance.",
        risk_level="medium",
    ),
]

BUSINESS_NAME_STEPS = [
    WorkflowStep(
        title="Search proposed business name on CAC portal",
        owner="assistant",
        rationale="Business name must be unique and must not use restricted words (Federal, National, Government).",
        risk_level="low",
    ),
    WorkflowStep(
        title="Collect proprietor/partner particulars",
        owner="legal_ops",
        rationale="CAC Form BN/1 requires: full name, address, nationality, occupation, and NIN/passport for each proprietor.",
        risk_level="low",
    ),
    WorkflowStep(
        title="File business name registration on CAC portal",
        owner="legal_ops",
        rationale="Registration must be completed within 60 days of commencing business (CAMA 2020, Part B).",
        risk_level="medium",
    ),
    WorkflowStep(
        title="Note 2-year renewal obligation in compliance calendar",
        owner="assistant",
        rationale="Business names must be renewed every 2 years. Set reminder 60 days before expiry.",
        risk_level="low",
    ),
]


def _get_formation_steps(entity_type: str) -> list[WorkflowStep]:
    et = entity_type.lower()
    if "business name" in et:
        return list(BUSINESS_NAME_STEPS)
    return list(CAC_WORKFLOW_STEPS)


def build_workflow(request: IntakeRequest) -> list[WorkflowStep]:
    sector = request.sector.lower()
    use_case = request.use_case.lower()

    steps = _get_formation_steps(request.entity_type)

    # Core intake step
    steps.insert(0, WorkflowStep(
        title="Validate founder facts and intended business activity",
        owner="legal_ops",
        rationale="A structured intake reduces drafting drift and keeps the workflow auditable.",
        risk_level="medium",
    ))

    steps.append(WorkflowStep(
        title=f"Map {request.entity_type} setup requirements into a draft compliance checklist",
        owner="assistant",
        rationale="Turn intake facts into a repeatable process checklist instead of free-form legal Q&A.",
        risk_level="medium",
    ))

    # Sector-specific regulatory steps
    if sector in REGULATED_SECTORS:
        steps.append(WorkflowStep(
            title="Escalate sector licensing review to counsel",
            owner="lawyer",
            rationale="Regulated sectors need counsel review before any operational recommendations are sent.",
            risk_level="high",
        ))

    if sector == "fintech":
        steps.append(WorkflowStep(
            title="Determine applicable CBN licensing tier (PSB / MMO / PSSP / Switching)",
            owner="lawyer",
            rationale="CBN licence must be confirmed before any live customer funds or payment processing. Licensing takes 6–18 months.",
            risk_level="high",
        ))
        steps.append(WorkflowStep(
            title="Complete SCUML registration (AML/CFT)",
            owner="legal_ops",
            rationale="SCUML registration is mandatory for fintech operators under the Money Laundering Act 2022.",
            risk_level="high",
        ))

    if sector == "health":
        steps.append(WorkflowStep(
            title="Assess NAFDAC product registration requirements",
            owner="lawyer",
            rationale="Health products must be registered with NAFDAC before market placement. Timeline: 3–18 months.",
            risk_level="high",
        ))

    if sector == "education":
        steps.append(WorkflowStep(
            title="Confirm FME accreditation or State approval requirements",
            owner="lawyer",
            rationale="Formal educational programmes require Ministry of Education approval. EdTech platforms must review NITDA guidelines for learner data.",
            risk_level="medium",
        ))

    if sector == "energy":
        steps.append(WorkflowStep(
            title="Review NERC licence requirements for electricity operations",
            owner="lawyer",
            rationale="Electricity generation, distribution, and trading each require a separate NERC licence.",
            risk_level="high",
        ))

    # Use-case specific steps
    if any(k in use_case for k in ("employee", "employment", "offer letter", "hire", "staff")):
        steps.append(WorkflowStep(
            title="Complete employment onboarding: PAYE, PENCOM, NSITF registrations",
            owner="legal_ops",
            rationale="Statutory registrations must be completed before first hire under Labour Act and Pension Reform Act 2014.",
            risk_level="high",
        ))
        steps.append(WorkflowStep(
            title="Draft employment contract compliant with Nigerian Labour Act",
            owner="lawyer",
            rationale="Written employment contract required for engagements exceeding 3 months (Labour Act s.7).",
            risk_level="high",
        ))

    if any(k in use_case for k in ("privacy", "data", "portal", "saas", "platform", "app", "software")):
        steps.append(WorkflowStep(
            title="Conduct data protection review: NDPA 2023 compliance",
            owner="lawyer",
            rationale="Customer-facing products collecting personal data require privacy policy, lawful basis confirmation, and DPIA where applicable.",
            risk_level="high",
        ))

    if any(k in use_case for k in ("contract", "nda", "vendor", "services", "agreement")):
        steps.append(WorkflowStep(
            title="Draft or review commercial agreement with issue-spotting memo",
            owner="lawyer",
            rationale="Commercial agreements require counsel review before execution — IP, liability cap, governing law, and payment terms.",
            risk_level="high",
        ))

    if any(k in use_case for k in ("trademark", "brand", "ip", "intellectual property")):
        steps.append(WorkflowStep(
            title="File trademark application with FIPO (Trademarks Registry)",
            owner="legal_ops",
            rationale="Trademark registration protects the brand. File early — Nigeria is first-to-file. Timeline: 18–36 months.",
            risk_level="medium",
        ))

    # Closing steps
    steps.extend([
        WorkflowStep(
            title="Generate compliance calendar for post-incorporation obligations",
            owner="assistant",
            rationale="Track all recurring obligations: CAC annual returns, CIT filing, PAYE, VAT, PENCOM, NDPA audit.",
            risk_level="medium",
        ),
        WorkflowStep(
            title="Lawyer sign-off on full matter packet",
            owner="lawyer",
            rationale="The platform escalates final legal judgment to a licensed Nigerian practitioner before delivery to client.",
            risk_level="high",
        ),
        WorkflowStep(
            title="Deliver next actions and compliance reminders to the client",
            owner="assistant",
            rationale="The output should be practical, structured, and explicit about remaining human review.",
            risk_level="low",
        ),
    ])
    return steps


def build_document_briefs(request: IntakeRequest) -> list[DocumentBrief]:
    briefs = [
        DocumentBrief(
            title="Company formation checklist",
            purpose="Convert founder facts into a source-backed action list for incorporation and onboarding.",
            sections=[
                "Founder details summary",
                "Entity type and sector assumptions",
                "Required filing inputs",
                "Open issues for lawyer review",
            ],
        ),
        DocumentBrief(
            title="Compliance calendar",
            purpose="Track post-formation obligations: CAC Annual Return, CIT, VAT, PAYE, PENCOM, NDPA audit.",
            sections=[
                "Immediate next steps",
                "Tax registration obligations",
                "Employment obligations",
                "Recurring annual/monthly deadlines",
                "Human review checkpoints",
            ],
        ),
    ]

    use_case = request.use_case.lower()

    if any(k in use_case for k in ("contract", "nda", "vendor", "services", "agreement")):
        briefs.append(DocumentBrief(
            title="Commercial agreement issue list",
            purpose="Outline a first-pass draft and flag clauses that need counsel review.",
            sections=[
                "Parties and scope",
                "Fees, VAT, and WHT treatment",
                "IP ownership and licence scope",
                "Termination and liability cap",
                "Governing law and dispute resolution",
                "Negotiation issues for counsel",
            ],
        ))

    if any(k in use_case for k in ("employee", "employment", "offer letter", "hire")):
        briefs.append(DocumentBrief(
            title="Employment packet outline",
            purpose="Prepare a structured draft packet for hiring and onboarding review.",
            sections=[
                "Role and compensation terms",
                "PAYE, PENCOM, NSITF obligations",
                "Contract terms per Labour Act",
                "Termination and restrictive covenant notes",
                "Counsel review checklist",
            ],
        ))

    if any(k in use_case for k in ("privacy", "data", "portal", "saas", "platform", "app")):
        briefs.append(DocumentBrief(
            title="Data protection compliance brief",
            purpose="Map product data flows to NDPA 2023 obligations with a counsel-reviewed compliance workstream.",
            sections=[
                "Data categories processed",
                "Lawful basis for each processing activity",
                "Consent capture and cookie policy",
                "Data subject rights procedure",
                "Breach notification workflow",
                "Vendor/processor DPA requirements",
                "DPIA assessment trigger checklist",
            ],
        ))

    if any(k in use_case for k in ("trademark", "brand", "ip", "intellectual property")):
        briefs.append(DocumentBrief(
            title="Trademark and IP brief",
            purpose="Outline trademark filing strategy and IP ownership structure.",
            sections=[
                "Mark description (word / logo / combined)",
                "Relevant Nice Classification classes",
                "Availability search results",
                "Filing strategy (Nigeria + Madrid Protocol)",
                "IP ownership in company structure",
            ],
        ))

    return briefs


def create_record(request: IntakeRequest) -> IntakeRecord:
    matter_id = str(uuid4())
    workflow = build_workflow(request)
    documents = build_document_briefs(request)
    sources = select_sources(
        request.entity_type,
        request.sector,
        request.use_case,
        jurisdiction=request.jurisdiction,
    )

    return IntakeRecord(
        id=str(uuid4()),
        matter_id=matter_id,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        jurisdiction=request.jurisdiction,
        founder_name=request.founder_name,
        business_name=request.business_name,
        entity_type=request.entity_type,
        sector=request.sector,
        use_case=request.use_case,
        contact_email=request.contact_email,
        consent=request.consent,
        status="pending_lawyer_review",
        workflow=workflow,
        documents=documents,
        sources=sources,
        disclaimers=build_disclaimers(request.jurisdiction),
    )
