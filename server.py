from __future__ import annotations

import json
import mimetypes
from datetime import date, datetime, timezone
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from legal_mvp.answers import generate_answer_draft
from legal_mvp.auth import (
    create_session,
    create_user,
    extract_bearer_token,
    is_session_valid,
    safe_user_dict,
    verify_password,
)
from legal_mvp.billing import (
    TIER_DEFINITIONS,
    create_billing_record,
    create_subscription,
)
from legal_mvp.compliance import generate_compliance_calendar, update_obligation_statuses
from legal_mvp.contract_review import create_contract_review, run_ai_contract_review
from legal_mvp.embeddings import get_embedding_backend_name, get_embedding_model_name
from legal_mvp.jurisdictions import DEFAULT_JURISDICTION, get_jurisdiction_pack, normalize_jurisdiction
from legal_mvp.matters import (
    build_answer_artifacts,
    build_matter_for_answer,
    build_matter_from_intake,
)
from legal_mvp.runtime_env import load_env_file
from legal_mvp.storage import (
    append_matter_artifacts,
    cancel_subscription,
    delete_session,
    get_answer_drafts,
    get_billing_records,
    get_compliance_obligations,
    get_contract_review,
    get_contract_reviews,
    get_generated_document,
    get_generated_documents,
    get_intakes,
    get_matters,
    get_review_queue,
    get_session,
    get_storage_backend_name,
    get_subscription_by_user,
    get_user_by_email,
    get_user_by_id,
    ingest_source_documents,
    initialize_storage,
    list_sources,
    list_users,
    matter_exists,
    review_answer_draft,
    save_answer_draft,
    save_billing_record,
    save_compliance_obligations,
    save_contract_review,
    save_generated_document,
    save_intake,
    save_session,
    save_subscription,
    save_user,
    search_citations,
    search_sources,
    update_compliance_obligation,
    update_contract_review,
    update_generated_document,
    update_user_matter_ids,
    upsert_matter,
)
from legal_mvp.email_service import (
    send_welcome,
    send_matter_created,
    send_contract_approved,
    send_payment_receipt,
)
from legal_mvp.paystack import initialize_transaction, verify_transaction, verify_webhook_signature
from legal_mvp.templates import fill_template, list_templates
from legal_mvp.workflows import build_intake_request, create_record
from legal_mvp.models import GeneratedDocument

load_env_file()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REVIEW_STATUS_BY_DECISION = {
    "approve": "approved_for_use",
    "reject": "rejected_by_lawyer",
}


def json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "CounselAI/1.0"

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _get_session(self) -> dict | None:
        token = extract_bearer_token(self.headers.get("Authorization", ""))
        if not token:
            return None
        session = get_session(token)
        if session and is_session_valid(session):
            return session
        return None

    def _require_auth(self, *allowed_roles: str) -> dict | None:
        """Returns session dict if authenticated and role is allowed, else sends 401/403 and returns None."""
        session = self._get_session()
        if not session:
            self.send_json({"error": "Authentication required."}, status=HTTPStatus.UNAUTHORIZED)
            return None
        if allowed_roles and session.get("role") not in allowed_roles:
            self.send_json({"error": "Insufficient permissions."}, status=HTTPStatus.FORBIDDEN)
            return None
        return session

    # ── Routing ───────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)
        requested_jurisdiction = qs.get("jurisdiction", [""])[0].strip()
        try:
            jurisdiction = normalize_jurisdiction(requested_jurisdiction or DEFAULT_JURISDICTION)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            # ── Public endpoints ──────────────────────────────────────────────
            if route == "/api/health":
                self.send_json({
                    "status": "ok",
                    "launch_jurisdiction": jurisdiction,
                    "app_title": get_jurisdiction_pack(jurisdiction).app_title,
                    "storage_backend": get_storage_backend_name(),
                    "embedding_backend": get_embedding_backend_name(),
                    "embedding_model": get_embedding_model_name(),
                })
                return

            if route == "/api/billing/tiers":
                self.send_json({"tiers": TIER_DEFINITIONS})
                return

            # ── Auth endpoints (GET) ──────────────────────────────────────────
            if route == "/api/auth/me":
                session = self._require_auth()
                if not session:
                    return
                user = get_user_by_id(session["user_id"])
                subscription = get_subscription_by_user(session["user_id"])
                self.send_json({
                    "user": safe_user_dict(user) if user else None,
                    "subscription": subscription,
                })
                return

            if route == "/api/users":
                if not self._require_auth("admin"):
                    return
                users = list_users()
                self.send_json({"items": [safe_user_dict(u) for u in users]})
                return

            # ── Core data endpoints (authenticated) ───────────────────────────
            if route == "/api/review-queue":
                session = self._require_auth("lawyer", "admin")
                if not session:
                    return
                items = get_review_queue()
                # Append overdue/due_soon compliance items
                obs = get_compliance_obligations()
                from datetime import date as _date
                today = _date.today()
                from legal_mvp.compliance import update_obligation_statuses
                obs = update_obligation_statuses(
                    [type("O", (), o)() for o in obs] if False else obs,  # keep as dicts
                    today,
                )
                for ob in obs:
                    if isinstance(ob, dict) and ob.get("status") in ("overdue", "due_soon"):
                        items.append({
                            "id": ob["id"],
                            "matter_id": ob["matter_id"],
                            "item_type": "compliance_alert",
                            "submitted_at": ob.get("due_date"),
                            "business_name": ob.get("obligation_type", "").replace("_", " ").title(),
                            "use_case": ob.get("description"),
                            "status": ob.get("status"),
                            "owner": "lawyer_review",
                        })
                self.send_json({"items": items[:20]})
                return

            if route == "/api/intakes":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                intakes = get_intakes()
                if session["role"] == "sme_founder":
                    user = get_user_by_id(session["user_id"])
                    my_ids = set(user.get("matter_ids", [])) if user else set()
                    intakes = [i for i in intakes if i.get("matter_id") in my_ids]
                self.send_json({"items": intakes})
                return

            if route == "/api/answer-drafts":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                self.send_json({"items": get_answer_drafts()})
                return

            if route == "/api/matters":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matters = get_matters()
                if session["role"] == "sme_founder":
                    user = get_user_by_id(session["user_id"])
                    my_ids = set(user.get("matter_ids", [])) if user else set()
                    matters = [m for m in matters if m.get("id") in my_ids]
                self.send_json({"items": matters})
                return

            if route == "/api/sources":
                self.send_json({"items": list_sources(jurisdiction=jurisdiction)})
                return

            if route == "/api/citation-search":
                query = qs.get("q", [""])[0].strip()
                if not query:
                    self.send_json({"items": []})
                    return
                self.send_json({"items": search_citations(query, jurisdiction=jurisdiction)})
                return

            if route == "/api/source-search":
                query = qs.get("q", [""])[0].strip()
                if not query:
                    self.send_json({"items": []})
                    return
                self.send_json({"items": search_sources(query, jurisdiction=jurisdiction)})
                return

            # ── Billing ───────────────────────────────────────────────────────
            if route == "/api/billing/subscription":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                target_user_id = qs.get("user_id", [session["user_id"]])[0]
                if session["role"] not in ("admin",) and target_user_id != session["user_id"]:
                    target_user_id = session["user_id"]
                sub = get_subscription_by_user(target_user_id)
                billing = get_billing_records(target_user_id)
                self.send_json({"subscription": sub, "billing_records": billing})
                return

            if route == "/api/billing/invoices":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                self.send_json({"items": get_billing_records(session["user_id"])})
                return

            # ── Compliance ────────────────────────────────────────────────────
            if route == "/api/compliance/calendar":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matter_id = qs.get("matter_id", [None])[0]
                obs = get_compliance_obligations(matter_id=matter_id)
                from datetime import date as _d
                overdue = sum(1 for o in obs if o.get("status") == "overdue")
                due_soon = sum(1 for o in obs if o.get("status") == "due_soon")
                self.send_json({"items": obs, "overdue_count": overdue, "due_soon_count": due_soon})
                return

            # ── Documents ─────────────────────────────────────────────────────
            if route == "/api/documents/templates":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                self.send_json({"templates": list_templates()})
                return

            if route == "/api/documents":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matter_id = qs.get("matter_id", [None])[0]
                docs = get_generated_documents(matter_id=matter_id)
                # Strip body_text from list
                self.send_json({"items": [{k: v for k, v in d.items() if k != "body_text"} for d in docs]})
                return

            if route.startswith("/api/documents/") and not route.endswith("/review"):
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                doc_id = route.removeprefix("/api/documents/").strip("/")
                doc = get_generated_document(doc_id)
                if not doc:
                    self.send_json({"error": "Document not found."}, status=HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"document": doc})
                return

            # ── Contracts ─────────────────────────────────────────────────────
            if route == "/api/contracts":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matter_id = qs.get("matter_id", [None])[0]
                self.send_json({"items": get_contract_reviews(matter_id=matter_id)})
                return

            if route.startswith("/api/contracts/") and not route.endswith(("/annotate", "/approve")):
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                review_id = route.removeprefix("/api/contracts/").strip("/")
                record = get_contract_review(review_id)
                if not record:
                    self.send_json({"error": "Contract review not found."}, status=HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"contract_review": record})
                return

            # ── Static files ──────────────────────────────────────────────────
            if route in {"/", "/index.html"}:
                self.serve_file(STATIC_DIR / "index.html")
                return
            if route == "/styles.css":
                self.serve_file(STATIC_DIR / "styles.css")
                return
            if route == "/app.js":
                self.serve_file(STATIC_DIR / "app.js")
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": f"Server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            payload = self.read_json()

            # ── Auth ──────────────────────────────────────────────────────────
            if path == "/api/auth/register":
                email = str(payload.get("email", "")).strip().lower()
                display_name = str(payload.get("display_name", "")).strip()
                role = str(payload.get("role", "sme_founder")).strip()
                password = str(payload.get("password", ""))
                if not email or not display_name or not password:
                    raise ValueError("email, display_name, and password are required.")
                if get_user_by_email(email):
                    raise ValueError("An account with this email already exists.")
                user = create_user(email, display_name, role, password)
                save_user(user.to_dict())
                session = create_session(user.to_dict())
                save_session(session.to_dict())
                try:
                    send_welcome(email, display_name)
                except Exception:
                    pass
                self.send_json({"user": safe_user_dict(user.to_dict()), "token": session.token}, status=HTTPStatus.CREATED)
                return

            if path == "/api/auth/login":
                email = str(payload.get("email", "")).strip().lower()
                password = str(payload.get("password", ""))
                user = get_user_by_email(email)
                if not user or not verify_password(user, password):
                    self.send_json({"error": "Invalid credentials."}, status=HTTPStatus.UNAUTHORIZED)
                    return
                if not user.get("is_active", True):
                    self.send_json({"error": "Account is inactive."}, status=HTTPStatus.FORBIDDEN)
                    return
                session = create_session(user)
                save_session(session.to_dict())
                self.send_json({"user": safe_user_dict(user), "token": session.token, "expires_at": session.expires_at})
                return

            if path == "/api/auth/logout":
                token = extract_bearer_token(self.headers.get("Authorization", ""))
                if token:
                    delete_session(token)
                self.send_json({"status": "logged_out"})
                return

            # ── Intakes ───────────────────────────────────────────────────────
            if path == "/api/intakes":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                request = build_intake_request(payload)
                record = create_record(request)
                save_intake(record)
                upsert_matter(build_matter_from_intake(record))
                update_user_matter_ids(session["user_id"], record.matter_id)
                # Auto-generate compliance calendar
                matter_dict = {"id": record.matter_id, "sector": record.sector,
                               "matter_type": record.entity_type, "summary": record.use_case}
                obligations = generate_compliance_calendar(matter_dict)
                save_compliance_obligations(record.matter_id, [o.to_dict() for o in obligations])
                user = get_user_by_id(session["user_id"])
                if user:
                    try:
                        send_matter_created(user["email"], user["display_name"], record.business_name, record.matter_id)
                    except Exception:
                        pass
                self.send_json(record.to_dict(), status=HTTPStatus.CREATED)
                return

            # ── Legal answers ─────────────────────────────────────────────────
            if path == "/api/legal-answer":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                question = payload.get("question")
                matter_id = payload.get("matter_id")
                jurisdiction = normalize_jurisdiction(payload.get("jurisdiction"))
                if not isinstance(question, str) or not question.strip():
                    raise ValueError("question must be a non-empty string.")
                if matter_id is not None and (not isinstance(matter_id, str) or not matter_id.strip()):
                    raise ValueError("matter_id must be a non-empty string when provided.")
                if isinstance(matter_id, str) and matter_id.strip() and not matter_exists(matter_id.strip()):
                    raise ValueError("matter_id does not match an existing matter.")
                citations = search_citations(question, limit=5, jurisdiction=jurisdiction)
                draft = generate_answer_draft(question, citations, jurisdiction=jurisdiction)
                if isinstance(matter_id, str) and matter_id.strip():
                    attached_matter_id = matter_id.strip()
                    draft["matter_id"] = attached_matter_id
                    tasks, approvals, document_versions = build_answer_artifacts(attached_matter_id, draft)
                    append_matter_artifacts(
                        attached_matter_id,
                        tasks=[task.to_dict() for task in tasks],
                        approvals=[approval.to_dict() for approval in approvals],
                        document_versions=[document.to_dict() for document in document_versions],
                        status=str(draft["review_status"]),
                        updated_at=str(draft["created_at"]),
                    )
                else:
                    matter = build_matter_for_answer(question, draft)
                    draft["matter_id"] = matter.id
                    upsert_matter(matter)
                    update_user_matter_ids(session["user_id"], matter.id)
                save_answer_draft(draft)
                self.send_json(draft, status=HTTPStatus.CREATED)
                return

            # ── Answer review ─────────────────────────────────────────────────
            if path.startswith("/api/answer-drafts/") and path.endswith("/review"):
                session = self._require_auth("lawyer", "admin")
                if not session:
                    return
                draft_id = path.removeprefix("/api/answer-drafts/").removesuffix("/review").strip("/")
                if not draft_id:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
                decision = payload.get("decision")
                reviewer_name = payload.get("reviewer_name") or safe_user_dict(get_user_by_id(session["user_id"]) or {}).get("display_name", "Lawyer")
                review_notes = payload.get("review_notes")
                if decision not in REVIEW_STATUS_BY_DECISION:
                    raise ValueError("decision must be approve or reject.")
                if not isinstance(reviewer_name, str) or not reviewer_name.strip():
                    raise ValueError("reviewer_name must be a non-empty string.")
                if decision == "reject" and not str(review_notes or "").strip():
                    raise ValueError("review_notes are required when rejecting a draft.")
                reviewed = review_answer_draft(
                    draft_id,
                    review_status=REVIEW_STATUS_BY_DECISION[decision],
                    reviewer_name=reviewer_name.strip(),
                    review_notes=str(review_notes or "").strip() or None,
                )
                self.send_json(reviewed)
                return

            # ── Source ingestion ──────────────────────────────────────────────
            if path == "/api/source-documents/ingest":
                if not self._require_auth("admin"):
                    return
                documents = payload.get("documents")
                result = ingest_source_documents(documents=documents)
                self.send_json(result, status=HTTPStatus.CREATED)
                return

            # ── Billing ───────────────────────────────────────────────────────
            if path == "/api/billing/subscribe":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                tier = str(payload.get("tier", "")).strip()
                seat_count = int(payload.get("seat_count", 1))
                billing_rec = create_billing_record(session["user_id"], tier, seat_count=seat_count)
                save_billing_record(billing_rec.to_dict())
                sub = create_subscription(session["user_id"], tier, seat_count=seat_count)
                save_subscription(sub.to_dict())
                self.send_json({"subscription": sub.to_dict(), "billing_record": billing_rec.to_dict()}, status=HTTPStatus.CREATED)
                return

            if path == "/api/billing/cancel":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                cancelled = cancel_subscription(session["user_id"])
                self.send_json({"subscription": cancelled})
                return

            # ── Compliance ────────────────────────────────────────────────────
            if path == "/api/compliance/calendar/generate":
                session = self._require_auth("lawyer", "admin", "sme_founder")
                if not session:
                    return
                matter_id = str(payload.get("matter_id", "")).strip()
                incorporation_date = payload.get("incorporation_date")
                if not matter_id or not matter_exists(matter_id):
                    raise ValueError("matter_id must reference an existing matter.")
                matters = get_matters()
                matter_dict = next((m for m in matters if m.get("id") == matter_id), {"id": matter_id, "sector": "", "summary": ""})
                if incorporation_date:
                    matter_dict["incorporation_date"] = incorporation_date
                obligations = generate_compliance_calendar(matter_dict, incorporation_date=incorporation_date)
                save_compliance_obligations(matter_id, [o.to_dict() for o in obligations])
                self.send_json({"items": [o.to_dict() for o in obligations], "generated": len(obligations)}, status=HTTPStatus.CREATED)
                return

            if path.startswith("/api/compliance/obligations/") and path.endswith("/complete"):
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                ob_id = path.removeprefix("/api/compliance/obligations/").removesuffix("/complete").strip("/")
                notes = payload.get("notes", "")
                now = datetime.now(timezone.utc).isoformat()
                updated = update_compliance_obligation(ob_id, {"status": "completed", "completed_at": now, "notes": notes, "updated_at": now})
                self.send_json({"obligation": updated})
                return

            if path.startswith("/api/compliance/obligations/") and path.endswith("/waive"):
                session = self._require_auth("admin")
                if not session:
                    return
                ob_id = path.removeprefix("/api/compliance/obligations/").removesuffix("/waive").strip("/")
                notes = payload.get("notes", "")
                now = datetime.now(timezone.utc).isoformat()
                updated = update_compliance_obligation(ob_id, {"status": "waived", "notes": notes, "updated_at": now})
                self.send_json({"obligation": updated})
                return

            # ── Document generation ───────────────────────────────────────────
            if path == "/api/documents/generate":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matter_id = str(payload.get("matter_id", "")).strip()
                template_key = str(payload.get("template_key", "")).strip()
                variables = payload.get("variables", {})
                if not matter_id or not matter_exists(matter_id):
                    raise ValueError("matter_id must reference an existing matter.")
                body_text = fill_template(template_key, variables)
                from uuid import uuid4
                now = datetime.now(timezone.utc).isoformat()
                doc = GeneratedDocument(
                    id=str(uuid4()),
                    matter_id=matter_id,
                    template_key=template_key,
                    title=variables.get("company_name") or template_key.replace("_", " ").title(),
                    body_text=body_text,
                    status="pending_review",
                    generated_at=now,
                    version_number=1,
                )
                save_generated_document(doc.to_dict())
                self.send_json({"document": doc.to_dict()}, status=HTTPStatus.CREATED)
                return

            if path.startswith("/api/documents/") and path.endswith("/review"):
                session = self._require_auth("lawyer", "admin")
                if not session:
                    return
                doc_id = path.removeprefix("/api/documents/").removesuffix("/review").strip("/")
                decision = payload.get("decision")
                if decision not in ("approve", "reject"):
                    raise ValueError("decision must be approve or reject.")
                now = datetime.now(timezone.utc).isoformat()
                updates = {
                    "status": "approved" if decision == "approve" else "rejected",
                    "approved_by_user_id": session["user_id"] if decision == "approve" else None,
                    "approved_at": now if decision == "approve" else None,
                }
                updated = update_generated_document(doc_id, updates)
                self.send_json({"document": updated})
                return

            # ── Contract review ───────────────────────────────────────────────
            if path == "/api/contracts/submit":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                matter_id = str(payload.get("matter_id", "")).strip()
                filename = str(payload.get("filename", "contract.txt")).strip()
                raw_text = str(payload.get("raw_text", "")).strip()
                if not matter_id or not matter_exists(matter_id):
                    raise ValueError("matter_id must reference an existing matter.")
                if not raw_text:
                    raise ValueError("raw_text must not be empty.")
                record = create_contract_review(matter_id, session["user_id"], filename, raw_text)
                record_dict = record.to_dict()
                save_contract_review(record_dict)
                # Run AI review synchronously
                record_dict = run_ai_contract_review(record_dict)
                update_contract_review(record_dict["id"], {
                    "extracted_clauses": record_dict["extracted_clauses"],
                    "risk_flags": record_dict["risk_flags"],
                    "ai_summary": record_dict["ai_summary"],
                    "status": record_dict["status"],
                    "updated_at": record_dict["updated_at"],
                })
                self.send_json({"contract_review": {k: v for k, v in record_dict.items() if k != "raw_text"}}, status=HTTPStatus.CREATED)
                return

            if path.startswith("/api/contracts/") and path.endswith("/annotate"):
                session = self._require_auth("lawyer", "admin")
                if not session:
                    return
                review_id = path.removeprefix("/api/contracts/").removesuffix("/annotate").strip("/")
                record = get_contract_review(review_id)
                if not record:
                    raise LookupError("Contract review not found.")
                annotation = {
                    "user_id": session["user_id"],
                    "clause_ref": payload.get("clause_ref"),
                    "annotation": payload.get("annotation"),
                    "severity": payload.get("severity", "medium"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                annotations = record.get("lawyer_annotations", [])
                annotations.append(annotation)
                now = datetime.now(timezone.utc).isoformat()
                updated = update_contract_review(review_id, {
                    "lawyer_annotations": annotations,
                    "status": "lawyer_annotating",
                    "updated_at": now,
                })
                self.send_json({"contract_review": updated})
                return

            if path.startswith("/api/contracts/") and path.endswith("/approve"):
                session = self._require_auth("lawyer", "admin")
                if not session:
                    return
                review_id = path.removeprefix("/api/contracts/").removesuffix("/approve").strip("/")
                notes = payload.get("notes", "")
                now = datetime.now(timezone.utc).isoformat()
                updated = update_contract_review(review_id, {
                    "status": "lawyer_approved",
                    "updated_at": now,
                    "lawyer_annotations": (get_contract_review(review_id) or {}).get("lawyer_annotations", []) + [{
                        "user_id": session["user_id"],
                        "annotation": notes or "Approved",
                        "clause_ref": "overall",
                        "severity": "info",
                        "created_at": now,
                    }],
                })
                # Email submitter
                cr = get_contract_review(review_id) or {}
                submitter = get_user_by_id(cr.get("submitted_by_user_id", ""))
                if submitter:
                    try:
                        send_contract_approved(submitter["email"], submitter["display_name"], cr.get("filename", "contract"))
                    except Exception:
                        pass
                self.send_json({"contract_review": updated})
                return

            # ── Paystack ──────────────────────────────────────────────────────
            if path == "/api/billing/paystack/initialize":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                tier = str(payload.get("tier", "")).strip()
                if tier not in ("starter", "growth", "scale", "law_firm"):
                    raise ValueError("Invalid tier.")
                user = get_user_by_id(session["user_id"])
                if not user:
                    raise LookupError("User not found.")
                tier_def = TIER_DEFINITIONS.get(tier, {})
                amount_ngn = float(tier_def.get("price_ngn", 0))
                if amount_ngn <= 0:
                    raise ValueError("This plan has no price configured.")
                data = initialize_transaction(
                    email=user["email"],
                    amount_ngn=amount_ngn,
                    tier=tier,
                    user_id=session["user_id"],
                )
                self.send_json({"authorization_url": data["authorization_url"], "reference": data["reference"]})
                return

            if path == "/api/billing/paystack/verify":
                session = self._require_auth("sme_founder", "lawyer", "admin")
                if not session:
                    return
                reference = str(payload.get("reference", "")).strip()
                if not reference:
                    raise ValueError("reference is required.")
                data = verify_transaction(reference)
                metadata = data.get("metadata", {})
                tier = metadata.get("tier", "starter")
                amount_ngn = data["amount"] / 100
                user = get_user_by_id(session["user_id"])
                # Create billing record + subscription
                billing_rec = create_billing_record(session["user_id"], tier, seat_count=1)
                billing_rec_dict = billing_rec.to_dict()
                billing_rec_dict["status"] = "paid"
                billing_rec_dict["description"] = f"Paystack payment — ref {reference}"
                save_billing_record(billing_rec_dict)
                sub = create_subscription(session["user_id"], tier, seat_count=1)
                save_subscription(sub.to_dict())
                if user:
                    try:
                        send_payment_receipt(user["email"], user["display_name"], tier, amount_ngn, reference)
                    except Exception:
                        pass
                self.send_json({"subscription": sub.to_dict(), "reference": reference})
                return

            if path == "/api/billing/paystack/webhook":
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length)
                sig = self.headers.get("x-paystack-signature", "")
                if not verify_webhook_signature(raw_body, sig):
                    self.send_json({"error": "Invalid signature."}, status=HTTPStatus.FORBIDDEN)
                    return
                event = json.loads(raw_body.decode())
                if event.get("event") == "charge.success":
                    ref  = event["data"]["reference"]
                    meta = event["data"].get("metadata", {})
                    tier = meta.get("tier", "starter")
                    user_id = meta.get("user_id", "")
                    amount_ngn = event["data"]["amount"] / 100
                    if user_id:
                        billing_rec = create_billing_record(user_id, tier, seat_count=1)
                        br = billing_rec.to_dict()
                        br["status"] = "paid"
                        br["description"] = f"Paystack webhook — ref {ref}"
                        save_billing_record(br)
                        sub = create_subscription(user_id, tier, seat_count=1)
                        save_subscription(sub.to_dict())
                        user = get_user_by_id(user_id)
                        if user:
                            try:
                                send_payment_receipt(user["email"], user["display_name"], tier, amount_ngn, ref)
                            except Exception:
                                pass
                self.send_json({"received": True})
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
        except json.JSONDecodeError:
            self.send_json({"error": "Request body must be valid JSON."}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": f"Unexpected server error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Static asset missing")
            return
        content_type, _ = mimetypes.guess_type(path.name)
        content_type = content_type or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    initialize_storage()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), AppHandler)
    print(
        "CounselAI running at http://127.0.0.1:8000 "
        f"using {get_storage_backend_name()} storage"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
