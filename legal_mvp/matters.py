from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from legal_mvp.jurisdictions import DEFAULT_JURISDICTION, normalize_jurisdiction
from legal_mvp.models import (
    ApprovalRecord,
    DocumentVersion,
    IntakeRecord,
    MatterRecord,
    MatterTask,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate_title(text: str, limit: int = 72) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def build_matter_from_intake(record: IntakeRecord) -> MatterRecord:
    created_at = record.submitted_at
    matter_id = record.matter_id
    tasks = [
        MatterTask(
            id=str(uuid4()),
            matter_id=matter_id,
            source_record_id=record.id,
            title=step.title,
            owner=step.owner,
            status="pending",
            risk_level=step.risk_level,
            rationale=step.rationale,
            created_at=created_at,
            updated_at=created_at,
        )
        for step in record.workflow
    ]
    approvals = [
        ApprovalRecord(
            id=str(uuid4()),
            matter_id=matter_id,
            artifact_type="workflow_packet",
            artifact_id=record.id,
            title="Workflow packet sign-off",
            status="pending_lawyer_review",
            requested_role="lawyer",
            requested_at=created_at,
        )
    ]
    document_versions = [
        DocumentVersion(
            id=str(uuid4()),
            matter_id=matter_id,
            title=document.title,
            document_type="workflow_brief",
            source_record_id=record.id,
            version_number=1,
            status="draft",
            summary=document.purpose,
            created_at=created_at,
            updated_at=created_at,
        )
        for document in record.documents
    ]
    return MatterRecord(
        id=matter_id,
        created_at=created_at,
        updated_at=created_at,
        title=record.business_name,
        client_name=record.founder_name,
        contact_email=record.contact_email,
        jurisdiction=record.jurisdiction,
        sector=record.sector,
        matter_type="founder_intake",
        status=record.status,
        source_record_type="intake",
        source_record_id=record.id,
        summary=record.use_case,
        tasks=tasks,
        approvals=approvals,
        document_versions=document_versions,
    )


def build_matter_for_answer(question: str, draft: dict[str, object]) -> MatterRecord:
    created_at = str(draft["created_at"])
    matter_id = str(uuid4())
    jurisdiction = normalize_jurisdiction(str(draft.get("jurisdiction", DEFAULT_JURISDICTION)))
    return MatterRecord(
        id=matter_id,
        created_at=created_at,
        updated_at=created_at,
        title=_truncate_title(question),
        client_name="Unassigned",
        contact_email="not-captured@example.com",
        jurisdiction=jurisdiction,
        sector="general",
        matter_type="legal_research",
        status="pending_lawyer_review",
        source_record_type="answer_draft",
        source_record_id=str(draft["id"]),
        summary=question,
        tasks=build_answer_tasks(matter_id, draft),
        approvals=build_answer_approvals(matter_id, draft),
        document_versions=build_answer_documents(matter_id, draft),
    )


def build_answer_tasks(matter_id: str, draft: dict[str, object]) -> list[MatterTask]:
    created_at = str(draft["created_at"])
    return [
        MatterTask(
            id=str(uuid4()),
            matter_id=matter_id,
            source_record_id=str(draft["id"]),
            title="Review cited legal answer draft",
            owner="lawyer" if bool(draft.get("requires_lawyer_review", True)) else "assistant",
            status="pending",
            risk_level=str(draft.get("risk_level", "high")),
            rationale="Cited answers should be tracked as reviewable legal operations artifacts.",
            created_at=created_at,
            updated_at=created_at,
        )
    ]


def build_answer_approvals(matter_id: str, draft: dict[str, object]) -> list[ApprovalRecord]:
    created_at = str(draft["created_at"])
    return [
        ApprovalRecord(
            id=str(uuid4()),
            matter_id=matter_id,
            artifact_type="legal_answer",
            artifact_id=str(draft["id"]),
            title="Legal answer approval",
            status=str(draft.get("review_status", "pending_lawyer_review")),
            requested_role="lawyer",
            requested_at=created_at,
            reviewer_name=draft.get("reviewer_name"),
            notes=draft.get("review_notes"),
            decided_at=draft.get("reviewed_at"),
        )
    ]


def build_answer_documents(matter_id: str, draft: dict[str, object]) -> list[DocumentVersion]:
    created_at = str(draft["created_at"])
    summary = str(draft.get("answer_text", "")).strip()
    summary = summary[:240] + ("..." if len(summary) > 240 else "")
    return [
        DocumentVersion(
            id=str(uuid4()),
            matter_id=matter_id,
            title="Cited legal answer draft",
            document_type="legal_answer",
            source_record_id=str(draft["id"]),
            version_number=1,
            status=_document_status_from_review(str(draft.get("review_status", "pending_lawyer_review"))),
            summary=summary,
            created_at=created_at,
            updated_at=created_at,
        )
    ]


def build_answer_artifacts(matter_id: str, draft: dict[str, object]) -> tuple[list[MatterTask], list[ApprovalRecord], list[DocumentVersion]]:
    return (
        build_answer_tasks(matter_id, draft),
        build_answer_approvals(matter_id, draft),
        build_answer_documents(matter_id, draft),
    )


def _document_status_from_review(review_status: str) -> str:
    if review_status == "approved_for_use":
        return "approved"
    if review_status == "rejected_by_lawyer":
        return "rejected"
    return "draft"


def derive_matter_status(approval_statuses: list[str]) -> str:
    normalized = [status for status in approval_statuses if status]
    if not normalized:
        return "in_progress"
    if any(status == "rejected_by_lawyer" for status in normalized):
        return "rejected_by_lawyer"
    if all(status == "approved_for_use" for status in normalized):
        return "approved_for_use"
    return "pending_lawyer_review"


def matter_waits_for_counsel(matter_status: str) -> bool:
    return matter_status == "pending_lawyer_review"
