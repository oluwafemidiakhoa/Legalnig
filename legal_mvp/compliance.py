"""Nigerian compliance calendar engine. Pure computation — no I/O."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from legal_mvp.models import ComplianceObligation

DUE_SOON_DAYS = 30

OBLIGATION_RULES: dict[str, dict] = {
    "tin_registration": {
        "description": "Tax Identification Number (TIN) registration with FIRS",
        "recurrence": "one_time",
        "basis": "Within 6 months of incorporation",
        "owner": "accountant",
        "area": "tax",
        "offset_days": 180,         # from incorporation date
        "always": True,
    },
    "cac_annual_return_first": {
        "description": "First CAC Annual Return filing (18 months post-incorporation)",
        "recurrence": "one_time",
        "basis": "18 months after Certificate of Incorporation date (CAMA 2020, s.417)",
        "owner": "lawyer",
        "area": "company_formation",
        "offset_days": 548,         # ~18 months
        "always": True,
    },
    "cac_annual_return": {
        "description": "CAC Annual Return — annual filing",
        "recurrence": "annual",
        "basis": "Annually on the anniversary of the first annual return (CAMA 2020)",
        "owner": "lawyer",
        "area": "company_formation",
        "offset_days": 913,         # ~30 months (second year onward)
        "always": True,
    },
    "firs_cit_filing": {
        "description": "Company Income Tax (CIT) return filing with FIRS",
        "recurrence": "annual",
        "basis": "By June 30 each year for financial year ending December 31 (CITA s.55)",
        "owner": "accountant",
        "area": "tax",
        "fixed_month": 6,
        "fixed_day": 30,
        "always": True,
    },
    "vat_registration": {
        "description": "VAT registration with FIRS (if annual turnover ≥ ₦25m)",
        "recurrence": "one_time",
        "basis": "Register once annual turnover reaches ₦25,000,000 (VAT Act s.8)",
        "owner": "accountant",
        "area": "tax",
        "offset_days": 180,
        "always": True,
    },
    "vat_return_jan": {
        "description": "VAT monthly return — January",
        "recurrence": "monthly",
        "basis": "21st of each month for preceding month's VAT (VAT Act s.15)",
        "owner": "accountant",
        "area": "tax",
        "fixed_month": 1,
        "fixed_day": 21,
        "always": True,
    },
    "paye_registration": {
        "description": "PAYE registration with State Internal Revenue Service (before first hire)",
        "recurrence": "one_time",
        "basis": "Before first employee is hired (PITA s.81)",
        "owner": "accountant",
        "area": "employment",
        "offset_days": 30,
        "requires_employees": True,
    },
    "nsitf_registration": {
        "description": "NSITF registration (Employee Compensation Scheme)",
        "recurrence": "one_time",
        "basis": "Before operations begin with employees (Employee Compensation Act 2010)",
        "owner": "hr",
        "area": "employment",
        "offset_days": 30,
        "requires_employees": True,
    },
    "pencom_registration": {
        "description": "Pension registration with PENCOM (3+ employees)",
        "recurrence": "one_time",
        "basis": "Organisations with 3 or more employees must register (Pension Reform Act 2014 s.2)",
        "owner": "hr",
        "area": "employment",
        "offset_days": 60,
        "requires_employees": True,
    },
    "pencom_remittance": {
        "description": "Monthly pension contribution remittance to PFA",
        "recurrence": "monthly",
        "basis": "Within 7 working days after salary payment (Pension Reform Act 2014 s.11)",
        "owner": "accountant",
        "area": "employment",
        "offset_days": 37,
        "requires_employees": True,
    },
    "ndpr_audit": {
        "description": "NDPA/NDPR annual data protection compliance audit",
        "recurrence": "annual",
        "basis": "Annual audit required for data controllers (NDPA 2023, s.26; NDPR 2019)",
        "owner": "lawyer",
        "area": "data_protection",
        "fixed_month": 3,
        "fixed_day": 31,
        "requires_data_processing": True,
    },
    "biz_name_renewal": {
        "description": "Business Name registration renewal (every 2 years)",
        "recurrence": "biennial",
        "basis": "Business names must be renewed every 2 years (CAMA 2020, Part B)",
        "owner": "lawyer",
        "area": "company_formation",
        "offset_days": 730,
        "entity_types": ["Business Name"],
    },
    "scuml_registration": {
        "description": "SCUML registration (AML/CFT compliance)",
        "recurrence": "one_time",
        "basis": "Required for designated non-financial businesses (Money Laundering Act 2022)",
        "owner": "lawyer",
        "area": "regulatory",
        "offset_days": 90,
        "regulated_sectors": ["fintech", "real_estate", "legal", "accounting"],
    },
    "cbn_license_review": {
        "description": "CBN licensing requirements review (fintech sector)",
        "recurrence": "one_time",
        "basis": "All fintech operators must determine applicable CBN licensing tier before launch",
        "owner": "lawyer",
        "area": "regulatory",
        "offset_days": 60,
        "regulated_sectors": ["fintech"],
    },
    "sec_registration_review": {
        "description": "SEC registration / exemption review (capital markets)",
        "recurrence": "one_time",
        "basis": "Any capital market activity requires SEC review (Investments and Securities Act 2007)",
        "owner": "lawyer",
        "area": "regulatory",
        "offset_days": 90,
        "regulated_sectors": ["fintech"],
    },
    "nafdac_registration": {
        "description": "NAFDAC product registration (health/food/pharma)",
        "recurrence": "one_time",
        "basis": "Required before placing regulated products on the Nigerian market (NAFDAC Act)",
        "owner": "lawyer",
        "area": "regulatory",
        "offset_days": 120,
        "regulated_sectors": ["health"],
    },
}


def _next_annual(month: int, day: int, from_date: date) -> date:
    """Return next occurrence of (month, day) on or after from_date."""
    candidate = date(from_date.year, month, day)
    if candidate < from_date:
        candidate = date(from_date.year + 1, month, day)
    return candidate


def generate_compliance_calendar(
    matter: dict,
    incorporation_date: str | None = None,
) -> list[ComplianceObligation]:
    """Generate compliance obligations for a matter based on its attributes."""
    from datetime import datetime, timezone

    today = date.today()
    base_date = today
    if incorporation_date:
        try:
            base_date = date.fromisoformat(incorporation_date[:10])
        except ValueError:
            base_date = today

    sector = (matter.get("sector") or "").lower()
    entity_type = matter.get("entity_type") or matter.get("matter_type") or ""
    # Detect employee obligation from matter summary or sector
    has_employees = bool(matter.get("has_employees")) or any(
        kw in (matter.get("summary") or "").lower()
        for kw in ("employee", "employment", "hire", "staff")
    )
    processes_data = any(
        kw in (matter.get("summary") or "").lower()
        for kw in ("data", "privacy", "portal", "saas", "platform", "app")
    ) or sector in ("fintech", "health", "education")

    now_iso = datetime.now(timezone.utc).isoformat()
    obligations: list[ComplianceObligation] = []

    for rule_key, rule in OBLIGATION_RULES.items():
        # ── Filter by requirement ──────────────────────────────────────────
        if rule.get("requires_employees") and not has_employees:
            continue
        if rule.get("requires_data_processing") and not processes_data:
            continue
        if rule.get("regulated_sectors") and sector not in rule["regulated_sectors"]:
            continue
        if rule.get("entity_types") and not any(et in entity_type for et in rule["entity_types"]):
            continue

        # ── Calculate due date ────────────────────────────────────────────
        if "fixed_month" in rule:
            due = _next_annual(rule["fixed_month"], rule["fixed_day"], today)
        elif "offset_days" in rule:
            due = base_date + timedelta(days=rule["offset_days"])
        else:
            due = today + timedelta(days=90)

        obligations.append(
            ComplianceObligation(
                id=str(uuid4()),
                matter_id=matter["id"],
                obligation_type=rule_key,
                description=rule["description"],
                due_date=due.isoformat(),
                status="upcoming",
                recurrence=rule["recurrence"],
                alert_sent=False,
                created_at=now_iso,
                updated_at=now_iso,
            )
        )

    # Deduplicate by obligation_type (keep earliest due date)
    by_type: dict[str, ComplianceObligation] = {}
    for ob in obligations:
        existing = by_type.get(ob.obligation_type)
        if existing is None or ob.due_date < existing.due_date:
            by_type[ob.obligation_type] = ob

    result = list(by_type.values())
    result.sort(key=lambda o: o.due_date)
    return update_obligation_statuses(result, today)


def update_obligation_statuses(
    obligations: list[ComplianceObligation], as_of_date: date
) -> list[ComplianceObligation]:
    """Refresh status of each obligation based on current date."""
    cutoff_soon = as_of_date + timedelta(days=DUE_SOON_DAYS)
    for ob in obligations:
        if ob.status in ("completed", "waived"):
            continue
        try:
            due = date.fromisoformat(ob.due_date)
        except ValueError:
            continue
        if due < as_of_date:
            ob.status = "overdue"
        elif due <= cutoff_soon:
            ob.status = "due_soon"
        else:
            ob.status = "upcoming"
    return obligations


def get_sector_compliance_pack(sector: str) -> list[dict]:
    """Return sector-specific regulatory checklist items."""
    SECTOR_PACKS: dict[str, list[dict]] = {
        "fintech": [
            {"item": "Determine CBN licensing tier (PSB / MMO / PSSP / Switching & Processing)", "priority": "critical"},
            {"item": "Obtain SCUML registration (AML/CFT)", "priority": "critical"},
            {"item": "Appoint a Money Laundering Reporting Officer (MLRO)", "priority": "high"},
            {"item": "Implement KYC/AML compliance programme", "priority": "high"},
            {"item": "Review SEC crowdfunding / investment advisory exemptions if applicable", "priority": "medium"},
            {"item": "Engage CBN-accredited compliance counsel before product launch", "priority": "critical"},
        ],
        "health": [
            {"item": "Determine NAFDAC registration requirements for products/services", "priority": "critical"},
            {"item": "Obtain medical facility registration with State Ministry of Health (if applicable)", "priority": "high"},
            {"item": "Comply with NDPR/NDPA for patient health data", "priority": "high"},
            {"item": "Review Telemedicine Guidelines (FMOH 2021) for digital health platforms", "priority": "medium"},
        ],
        "education": [
            {"item": "Obtain Federal Ministry of Education accreditation / state approval (if formal education)", "priority": "high"},
            {"item": "Review NITDA Guidelines for EdTech platforms collecting learner data", "priority": "high"},
            {"item": "Comply with NDPR/NDPA for learner data", "priority": "high"},
        ],
        "logistics": [
            {"item": "Register with FRSC for commercial vehicle operations (if applicable)", "priority": "medium"},
            {"item": "Obtain State Ministry of Transport / LASG operating permit", "priority": "medium"},
            {"item": "Ensure driver and vehicle insurance coverage meets regulatory minimums", "priority": "high"},
        ],
        "energy": [
            {"item": "Obtain NERC licence for electricity generation, distribution, or trading", "priority": "critical"},
            {"item": "Comply with DPR / NUPRC requirements for petroleum operations (if applicable)", "priority": "high"},
            {"item": "Review ESIA requirements under NESREA for large projects", "priority": "medium"},
        ],
    }
    return SECTOR_PACKS.get(sector.lower(), [])
