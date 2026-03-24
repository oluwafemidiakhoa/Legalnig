from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from legal_mvp.embeddings import (
    embed_text,
    embed_texts,
    get_embedding_backend_name,
    vector_literal,
)
from legal_mvp.ingestion import build_source_document, chunk_text, content_hash
from legal_mvp.jurisdictions import DEFAULT_JURISDICTION, normalize_jurisdiction
from legal_mvp.matters import derive_matter_status, matter_waits_for_counsel
from legal_mvp.models import (
    IntakeRecord,
    LegalSource,
    MatterRecord,
    SourceDocument,
)
from legal_mvp.runtime_env import load_env_file
from legal_mvp.source_corpus import SEED_SOURCE_DOCUMENTS
from legal_mvp.sources import BASE_SOURCES


load_env_file()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INTAKES_FILE = DATA_DIR / "intakes.json"
QUEUE_FILE = DATA_DIR / "review_queue.json"
SOURCE_DOCS_FILE = DATA_DIR / "source_documents.json"
ANSWER_DRAFTS_FILE = DATA_DIR / "answer_drafts.json"
MATTERS_FILE = DATA_DIR / "matters.json"
SQL_DIR = ROOT / "sql"
SCHEMA_FILE = SQL_DIR / "001_init_pgvector.sql"


class JsonStorageBackend:
    name = "json"

    def initialize(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        _new_json_files = [
            DATA_DIR / "users.json",
            DATA_DIR / "sessions.json",
            DATA_DIR / "billing_records.json",
            DATA_DIR / "subscriptions.json",
            DATA_DIR / "compliance_obligations.json",
            DATA_DIR / "generated_documents.json",
            DATA_DIR / "contract_reviews.json",
        ]
        for path in _new_json_files:
            if not path.exists():
                path.write_text("[]", encoding="utf-8")
        for path in (INTAKES_FILE, QUEUE_FILE, SOURCE_DOCS_FILE, ANSWER_DRAFTS_FILE, MATTERS_FILE):
            if not path.exists():
                if path == SOURCE_DOCS_FILE:
                    path.write_text(
                        json.dumps([document.to_dict() for document in SEED_SOURCE_DOCUMENTS], indent=2),
                        encoding="utf-8",
                    )
                else:
                    path.write_text("[]", encoding="utf-8")
        raw = SOURCE_DOCS_FILE.read_text(encoding="utf-8")
        source_records = json.loads(raw) if raw.strip() else []
        existing_keys = {item["source_key"] for item in source_records if "source_key" in item}
        changed = False
        for document in SEED_SOURCE_DOCUMENTS:
            if document.source_key not in existing_keys:
                source_records.append(document.to_dict())
                changed = True
        if changed:
            self._write_records(SOURCE_DOCS_FILE, sorted(source_records, key=lambda item: item["source_key"]))

    def _load_records(self, path: Path) -> list[dict[str, Any]]:
        self.initialize()
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        return json.loads(raw)

    def _write_records(self, path: Path, records: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def _append_record(self, path: Path, record: dict[str, Any]) -> None:
        records = self._load_records(path)
        records.append(record)
        self._write_records(path, records)

    def _load_source_documents(self) -> list[SourceDocument]:
        return [build_source_document(item) for item in self._load_records(SOURCE_DOCS_FILE)]

    def _load_matters(self) -> list[dict[str, Any]]:
        return self._load_records(MATTERS_FILE)

    def _write_matters(self, matters: list[dict[str, Any]]) -> None:
        self._write_records(MATTERS_FILE, matters)

    def save_intake(self, record: IntakeRecord) -> None:
        self._append_record(INTAKES_FILE, record.to_dict())

    def get_intakes(self) -> list[dict[str, Any]]:
        intakes = self._load_records(INTAKES_FILE)
        return [_normalize_intake_record(item) for item in reversed(intakes[-10:])]

    def enqueue_review(self, record: IntakeRecord) -> None:
        queue_item = {
            "id": record.id,
            "matter_id": record.matter_id,
            "submitted_at": record.submitted_at,
            "business_name": record.business_name,
            "use_case": record.use_case,
            "sector": record.sector,
            "status": record.status,
            "owner": "lawyer_review",
        }
        self._append_record(QUEUE_FILE, queue_item)

    def get_review_queue(self) -> list[dict[str, Any]]:
        matters = self.get_matters()
        items = []
        for matter in matters:
            if not matter_waits_for_counsel(str(matter.get("status", ""))):
                continue
            items.append(
                {
                    "id": matter["id"],
                    "matter_id": matter["id"],
                    "submitted_at": matter["updated_at"],
                    "business_name": matter["title"],
                    "use_case": matter["summary"],
                    "jurisdiction": matter.get("jurisdiction", DEFAULT_JURISDICTION),
                    "sector": matter["sector"],
                    "status": matter["status"],
                    "owner": "lawyer_review",
                }
            )
        return items[:10]

    def save_answer_draft(self, draft: dict[str, Any]) -> None:
        self._append_record(ANSWER_DRAFTS_FILE, draft)

    def get_answer_drafts(self) -> list[dict[str, Any]]:
        drafts = self._load_records(ANSWER_DRAFTS_FILE)
        return [_normalize_answer_draft(item) for item in reversed(drafts[-10:])]

    def review_answer_draft(
        self,
        draft_id: str,
        review_status: str,
        reviewer_name: str,
        review_notes: str | None,
    ) -> dict[str, Any]:
        drafts = self._load_records(ANSWER_DRAFTS_FILE)
        reviewed_at = datetime.now(timezone.utc).isoformat()
        reviewed: dict[str, Any] | None = None
        for draft in drafts:
            if draft.get("id") != draft_id:
                continue
            draft["review_status"] = review_status
            draft["reviewer_name"] = reviewer_name
            draft["review_notes"] = review_notes or None
            draft["reviewed_at"] = reviewed_at
            reviewed = draft
            break
        if reviewed is None:
            raise LookupError("Answer draft not found.")
        self._write_records(ANSWER_DRAFTS_FILE, drafts)
        self.sync_answer_review(reviewed)
        return reviewed

    def upsert_matter(self, matter: MatterRecord | dict[str, Any]) -> dict[str, Any]:
        matter_dict = matter.to_dict() if isinstance(matter, MatterRecord) else matter
        matters = self._load_matters()
        replaced = False
        for index, item in enumerate(matters):
            if item["id"] == matter_dict["id"]:
                matters[index] = matter_dict
                replaced = True
                break
        if not replaced:
            matters.append(matter_dict)
        self._write_matters(matters)
        return matter_dict

    def append_matter_artifacts(
        self,
        matter_id: str,
        tasks: list[dict[str, Any]],
        approvals: list[dict[str, Any]],
        document_versions: list[dict[str, Any]],
        status: str,
        updated_at: str,
    ) -> dict[str, Any]:
        matters = self._load_matters()
        for matter in matters:
            if matter["id"] != matter_id:
                continue
            matter["updated_at"] = updated_at
            matter["tasks"] = self._merge_by_id(matter.get("tasks", []), tasks)
            matter["approvals"] = self._merge_by_id(matter.get("approvals", []), approvals)
            matter["document_versions"] = self._merge_by_id(
                matter.get("document_versions", []),
                document_versions,
            )
            matter["status"] = derive_matter_status(
                [str(item.get("status", "")) for item in matter.get("approvals", [])]
            )
            self._write_matters(matters)
            return matter
        raise LookupError("Matter not found.")

    def get_matters(self) -> list[dict[str, Any]]:
        matters = self._load_matters()
        return [_normalize_matter_record(item) for item in reversed(matters[-10:])]

    def matter_exists(self, matter_id: str) -> bool:
        return any(item["id"] == matter_id for item in self._load_matters())

    def sync_answer_review(self, reviewed_draft: dict[str, Any]) -> None:
        matter_id = reviewed_draft.get("matter_id")
        if not matter_id:
            return
        matters = self._load_matters()
        for matter in matters:
            if matter["id"] != matter_id:
                continue
            matter["updated_at"] = reviewed_draft.get("reviewed_at") or datetime.now(timezone.utc).isoformat()
            for task in matter.get("tasks", []):
                if task.get("source_record_id") == reviewed_draft["id"]:
                    task["status"] = "completed" if reviewed_draft["review_status"] == "approved_for_use" else "blocked"
                    task["updated_at"] = matter["updated_at"]
            for approval in matter.get("approvals", []):
                if approval.get("artifact_id") == reviewed_draft["id"]:
                    approval["status"] = reviewed_draft["review_status"]
                    approval["reviewer_name"] = reviewed_draft.get("reviewer_name")
                    approval["notes"] = reviewed_draft.get("review_notes")
                    approval["decided_at"] = reviewed_draft.get("reviewed_at")
            for document in matter.get("document_versions", []):
                if document.get("source_record_id") == reviewed_draft["id"]:
                    document["status"] = _document_status_from_review(reviewed_draft["review_status"])
                    document["updated_at"] = matter["updated_at"]
            matter["status"] = derive_matter_status(
                [str(item.get("status", "")) for item in matter.get("approvals", [])]
            )
            self._write_matters(matters)
            return

    def list_sources(self, jurisdiction: str | None = None) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        return [
            asdict(source)
            for source in BASE_SOURCES
            if source.jurisdiction == active_jurisdiction
        ]

    def search_sources(
        self,
        query: str,
        limit: int = 5,
        jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        query_terms = {part for part in query.lower().split() if part}
        if not query_terms:
            return self.list_sources(jurisdiction=active_jurisdiction)[:limit]

        def score(source: LegalSource) -> tuple[int, str]:
            haystack = f"{source.title} {source.issuer} {source.area} {source.usage_note}".lower()
            return (sum(term in haystack for term in query_terms), source.title)

        ranked = sorted(
            [source for source in BASE_SOURCES if source.jurisdiction == active_jurisdiction],
            key=score,
            reverse=True,
        )
        return [asdict(source) for source in ranked[:limit]]

    def ingest_source_documents(self, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        self.initialize()
        existing = {
            item["source_key"]: item
            for item in self._load_records(SOURCE_DOCS_FILE)
            if "source_key" in item
        }
        documents_to_write = documents or [document.to_dict() for document in SEED_SOURCE_DOCUMENTS]
        parsed_documents = [build_source_document(item) for item in documents_to_write]
        for document in parsed_documents:
            existing[document.source_key] = document.to_dict()
        ordered = sorted(existing.values(), key=lambda item: item["source_key"])
        self._write_records(SOURCE_DOCS_FILE, ordered)
        chunk_count = sum(len(chunk_text(document["body_text"])) for document in ordered)
        return {
            "documents": len(parsed_documents),
            "chunks": chunk_count,
            "embedding_backend": get_embedding_backend_name(),
        }

    def search_citations(
        self,
        query: str,
        limit: int = 5,
        jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        query_terms = {part for part in query.lower().split() if part}
        if not query_terms:
            return []

        matches: list[dict[str, Any]] = []
        for document in self._load_source_documents():
            if document.jurisdiction != active_jurisdiction:
                continue
            for chunk in chunk_text(document.body_text):
                normalized_chunk = chunk.lower()
                score = sum(term in normalized_chunk for term in query_terms)
                if score == 0:
                    continue
                matches.append(
                    {
                        "title": document.title,
                        "issuer": document.issuer,
                        "area": document.area,
                        "jurisdiction": document.jurisdiction,
                        "citation_label": document.citation_label,
                        "canonical_url": document.canonical_url,
                        "snippet": chunk,
                        "production_ready": document.production_ready,
                        "similarity": round(score / max(len(query_terms), 1), 4),
                    }
                )
        matches.sort(key=lambda item: item["similarity"], reverse=True)
        return matches[:limit]

    def _merge_by_id(self, existing: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged = {item["id"]: item for item in existing}
        for item in updates:
            merged[item["id"]] = item
        return list(merged.values())

    # ── Auth ───────────────────────────────────────────────────────────────────

    def save_user(self, record: dict[str, Any]) -> None:
        users = self._load_records(DATA_DIR / "users.json")
        users = [u for u in users if u.get("id") != record["id"]]
        users.append(record)
        self._write_records(DATA_DIR / "users.json", users)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        for u in self._load_records(DATA_DIR / "users.json"):
            if u.get("email", "").lower() == email.lower():
                return u
        return None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for u in self._load_records(DATA_DIR / "users.json"):
            if u.get("id") == user_id:
                return u
        return None

    def list_users(self) -> list[dict[str, Any]]:
        return self._load_records(DATA_DIR / "users.json")

    def save_session(self, session: dict[str, Any]) -> None:
        sessions = self._load_records(DATA_DIR / "sessions.json")
        sessions = [s for s in sessions if s.get("token") != session["token"]]
        sessions.append(session)
        self._write_records(DATA_DIR / "sessions.json", sessions)

    def get_session(self, token: str) -> dict[str, Any] | None:
        for s in self._load_records(DATA_DIR / "sessions.json"):
            if s.get("token") == token:
                return s
        return None

    def delete_session(self, token: str) -> None:
        sessions = self._load_records(DATA_DIR / "sessions.json")
        self._write_records(DATA_DIR / "sessions.json", [s for s in sessions if s.get("token") != token])

    def update_user_matter_ids(self, user_id: str, matter_id: str) -> None:
        users = self._load_records(DATA_DIR / "users.json")
        for u in users:
            if u.get("id") == user_id:
                ids = u.get("matter_ids", [])
                if matter_id not in ids:
                    ids.append(matter_id)
                u["matter_ids"] = ids
        self._write_records(DATA_DIR / "users.json", users)

    # ── Billing ────────────────────────────────────────────────────────────────

    def save_billing_record(self, record: dict[str, Any]) -> None:
        self._append_record(DATA_DIR / "billing_records.json", record)

    def save_subscription(self, record: dict[str, Any]) -> None:
        subs = self._load_records(DATA_DIR / "subscriptions.json")
        subs = [s for s in subs if s.get("id") != record["id"]]
        subs.append(record)
        self._write_records(DATA_DIR / "subscriptions.json", subs)

    def get_subscription_by_user(self, user_id: str) -> dict[str, Any] | None:
        for s in self._load_records(DATA_DIR / "subscriptions.json"):
            if s.get("user_id") == user_id and s.get("status") == "active":
                return s
        return None

    def cancel_subscription(self, user_id: str) -> dict[str, Any] | None:
        subs = self._load_records(DATA_DIR / "subscriptions.json")
        cancelled = None
        for s in subs:
            if s.get("user_id") == user_id and s.get("status") == "active":
                s["status"] = "cancelled"
                s["cancelled_at"] = datetime.now(timezone.utc).isoformat()
                cancelled = s
        self._write_records(DATA_DIR / "subscriptions.json", subs)
        return cancelled

    def get_billing_records(self, user_id: str) -> list[dict[str, Any]]:
        return [r for r in self._load_records(DATA_DIR / "billing_records.json") if r.get("user_id") == user_id]

    # ── Compliance ─────────────────────────────────────────────────────────────

    def save_compliance_obligations(self, matter_id: str, obligations: list[dict[str, Any]]) -> None:
        existing = self._load_records(DATA_DIR / "compliance_obligations.json")
        existing = [o for o in existing if o.get("matter_id") != matter_id]
        existing.extend(obligations)
        self._write_records(DATA_DIR / "compliance_obligations.json", existing)

    def get_compliance_obligations(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        all_obs = self._load_records(DATA_DIR / "compliance_obligations.json")
        if matter_id:
            return [o for o in all_obs if o.get("matter_id") == matter_id]
        return all_obs

    def update_compliance_obligation(self, obligation_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        obs = self._load_records(DATA_DIR / "compliance_obligations.json")
        found = None
        for ob in obs:
            if ob.get("id") == obligation_id:
                ob.update(updates)
                found = ob
        if found is None:
            raise LookupError("Compliance obligation not found.")
        self._write_records(DATA_DIR / "compliance_obligations.json", obs)
        return found

    # ── Generated documents ────────────────────────────────────────────────────

    def save_generated_document(self, doc: dict[str, Any]) -> None:
        self._append_record(DATA_DIR / "generated_documents.json", doc)

    def get_generated_documents(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        docs = self._load_records(DATA_DIR / "generated_documents.json")
        if matter_id:
            return [d for d in docs if d.get("matter_id") == matter_id]
        return list(reversed(docs[-20:]))

    def get_generated_document(self, doc_id: str) -> dict[str, Any] | None:
        for d in self._load_records(DATA_DIR / "generated_documents.json"):
            if d.get("id") == doc_id:
                return d
        return None

    def update_generated_document(self, doc_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        docs = self._load_records(DATA_DIR / "generated_documents.json")
        found = None
        for d in docs:
            if d.get("id") == doc_id:
                d.update(updates)
                found = d
        if found is None:
            raise LookupError("Generated document not found.")
        self._write_records(DATA_DIR / "generated_documents.json", docs)
        return found

    # ── Contract reviews ───────────────────────────────────────────────────────

    def save_contract_review(self, record: dict[str, Any]) -> None:
        self._append_record(DATA_DIR / "contract_reviews.json", record)

    def get_contract_reviews(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        records = self._load_records(DATA_DIR / "contract_reviews.json")
        if matter_id:
            records = [r for r in records if r.get("matter_id") == matter_id]
        # Omit raw_text from list view
        return [{k: v for k, v in r.items() if k != "raw_text"} for r in list(reversed(records[-20:]))]

    def get_contract_review(self, review_id: str) -> dict[str, Any] | None:
        for r in self._load_records(DATA_DIR / "contract_reviews.json"):
            if r.get("id") == review_id:
                return r
        return None

    def update_contract_review(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        records = self._load_records(DATA_DIR / "contract_reviews.json")
        found = None
        for r in records:
            if r.get("id") == review_id:
                r.update(updates)
                found = r
        if found is None:
            raise LookupError("Contract review not found.")
        self._write_records(DATA_DIR / "contract_reviews.json", records)
        return found


class PostgresStorageBackend:
    name = "postgres"

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def initialize(self) -> None:
        schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
        schema2_file = SQL_DIR / "002_auth_billing_compliance.sql"
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
                if schema2_file.exists():
                    cur.execute(schema2_file.read_text(encoding="utf-8"))
            conn.commit()
        self.seed_sources()
        self.ingest_source_documents()

    def seed_sources(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                allowed_titles_by_area: dict[tuple[str, str], list[str]] = {}
                for source in BASE_SOURCES:
                    allowed_titles_by_area.setdefault((source.jurisdiction, source.area), []).append(source.title)
                    embedding = self._source_embedding(source)
                    cur.execute(
                        """
                        INSERT INTO legal_sources (
                            title,
                            issuer,
                            jurisdiction,
                            area,
                            usage_note,
                            production_ready,
                            embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (title, area) DO UPDATE
                        SET issuer = EXCLUDED.issuer,
                            jurisdiction = EXCLUDED.jurisdiction,
                            usage_note = EXCLUDED.usage_note,
                            production_ready = EXCLUDED.production_ready,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                        """,
                        (
                            source.title,
                            source.issuer,
                            source.jurisdiction,
                            source.area,
                            source.usage_note,
                            source.production_ready,
                            embedding,
                        ),
                    )
                for (jurisdiction, area), titles in allowed_titles_by_area.items():
                    cur.execute(
                        """
                        DELETE FROM legal_sources
                        WHERE jurisdiction = %s
                          AND area = %s
                          AND title <> ALL(%s::text[])
                        """,
                        (jurisdiction, area, titles),
                    )
            conn.commit()

    def save_intake(self, record: IntakeRecord) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO intakes (
                        id,
                        matter_id,
                        submitted_at,
                        jurisdiction,
                        founder_name,
                        business_name,
                        entity_type,
                        sector,
                        use_case,
                        contact_email,
                        consent,
                        status,
                        workflow,
                        documents,
                        sources,
                        disclaimers,
                        query_embedding
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::vector
                    )
                    """,
                    (
                        record.id,
                        record.matter_id,
                        record.submitted_at,
                        record.jurisdiction,
                        record.founder_name,
                        record.business_name,
                        record.entity_type,
                        record.sector,
                        record.use_case,
                        record.contact_email,
                        record.consent,
                        record.status,
                        json.dumps([asdict(item) for item in record.workflow]),
                        json.dumps([asdict(item) for item in record.documents]),
                        json.dumps([asdict(item) for item in record.sources]),
                        json.dumps(record.disclaimers),
                        self._query_embedding(record.use_case, record.sector, record.jurisdiction),
                    ),
                )
            conn.commit()

    def get_intakes(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        matter_id,
                        submitted_at,
                        jurisdiction,
                        founder_name,
                        business_name,
                        entity_type,
                        sector,
                        use_case,
                        contact_email,
                        consent,
                        status,
                        workflow,
                        documents,
                        sources,
                        disclaimers
                    FROM intakes
                    ORDER BY submitted_at DESC
                    LIMIT 10
                    """
                )
                return self._normalize_rows(list(cur.fetchall()))

    def enqueue_review(self, record: IntakeRecord) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO review_queue (
                        intake_id,
                        submitted_at,
                        business_name,
                        use_case,
                        sector,
                        status,
                        owner
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (intake_id) DO UPDATE
                    SET submitted_at = EXCLUDED.submitted_at,
                        business_name = EXCLUDED.business_name,
                        use_case = EXCLUDED.use_case,
                        sector = EXCLUDED.sector,
                        status = EXCLUDED.status,
                        owner = EXCLUDED.owner
                    """,
                    (
                        record.id,
                        record.submitted_at,
                        record.business_name,
                        record.use_case,
                        record.sector,
                        record.status,
                        "lawyer_review",
                    ),
                )
            conn.commit()

    def get_review_queue(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        id AS matter_id,
                        updated_at AS submitted_at,
                        title AS business_name,
                        summary AS use_case,
                        jurisdiction,
                        sector,
                        status,
                        'lawyer_review' AS owner
                    FROM matters
                    WHERE status = 'pending_lawyer_review'
                    ORDER BY updated_at DESC
                    LIMIT 10
                    """
                )
                return self._normalize_rows(list(cur.fetchall()))

    def save_answer_draft(self, draft: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO answer_drafts (
                        id,
                        matter_id,
                        created_at,
                        jurisdiction,
                        question,
                        status,
                        answer_text,
                        risk_level,
                        requires_lawyer_review,
                        recommended_actions,
                        follow_up_questions,
                        citations,
                        model,
                        review_status,
                        reviewer_name,
                        review_notes,
                        reviewed_at,
                        disclaimer
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        draft["id"],
                        draft.get("matter_id"),
                        draft["created_at"],
                        draft.get("jurisdiction", DEFAULT_JURISDICTION),
                        draft["question"],
                        draft["status"],
                        draft["answer_text"],
                        draft["risk_level"],
                        draft["requires_lawyer_review"],
                        json.dumps(draft["recommended_actions"]),
                        json.dumps(draft["follow_up_questions"]),
                        json.dumps(draft["citations"]),
                        draft["model"],
                        draft["review_status"],
                        draft.get("reviewer_name"),
                        draft.get("review_notes"),
                        draft.get("reviewed_at"),
                        draft["disclaimer"],
                    ),
                )
            conn.commit()

    def get_answer_drafts(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        matter_id,
                        created_at,
                        jurisdiction,
                        question,
                        status,
                        answer_text,
                        risk_level,
                        requires_lawyer_review,
                        recommended_actions,
                        follow_up_questions,
                        citations,
                        model,
                        review_status,
                        reviewer_name,
                        review_notes,
                        reviewed_at,
                        disclaimer
                    FROM answer_drafts
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                )
                return self._normalize_rows(list(cur.fetchall()))

    def review_answer_draft(
        self,
        draft_id: str,
        review_status: str,
        reviewer_name: str,
        review_notes: str | None,
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE answer_drafts
                    SET review_status = %s,
                        reviewer_name = %s,
                        review_notes = %s,
                        reviewed_at = NOW()
                    WHERE id = %s
                    RETURNING
                        id,
                        matter_id,
                        created_at,
                        jurisdiction,
                        question,
                        status,
                        answer_text,
                        risk_level,
                        requires_lawyer_review,
                        recommended_actions,
                        follow_up_questions,
                        citations,
                        model,
                        review_status,
                        reviewer_name,
                        review_notes,
                        reviewed_at,
                        disclaimer
                    """,
                    (
                        review_status,
                        reviewer_name,
                        review_notes or None,
                        draft_id,
                    ),
                )
                reviewed = cur.fetchone()
            conn.commit()
        if reviewed is None:
            raise LookupError("Answer draft not found.")
        self.sync_answer_review(reviewed)
        return reviewed

    def upsert_matter(self, matter: MatterRecord | dict[str, Any]) -> dict[str, Any]:
        matter_dict = matter.to_dict() if isinstance(matter, MatterRecord) else matter
        tasks = matter_dict.pop("tasks", [])
        approvals = matter_dict.pop("approvals", [])
        document_versions = matter_dict.pop("document_versions", [])
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO matters (
                        id,
                        created_at,
                        updated_at,
                        title,
                        client_name,
                        contact_email,
                        jurisdiction,
                        sector,
                        matter_type,
                        status,
                        source_record_type,
                        source_record_id,
                        summary
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET updated_at = EXCLUDED.updated_at,
                        title = EXCLUDED.title,
                        client_name = EXCLUDED.client_name,
                        contact_email = EXCLUDED.contact_email,
                        jurisdiction = EXCLUDED.jurisdiction,
                        sector = EXCLUDED.sector,
                        matter_type = EXCLUDED.matter_type,
                        status = EXCLUDED.status,
                        source_record_type = EXCLUDED.source_record_type,
                        source_record_id = EXCLUDED.source_record_id,
                        summary = EXCLUDED.summary
                    """,
                    (
                        matter_dict["id"],
                        matter_dict["created_at"],
                        matter_dict["updated_at"],
                        matter_dict["title"],
                        matter_dict["client_name"],
                        matter_dict["contact_email"],
                        matter_dict.get("jurisdiction", DEFAULT_JURISDICTION),
                        matter_dict["sector"],
                        matter_dict["matter_type"],
                        matter_dict["status"],
                        matter_dict["source_record_type"],
                        matter_dict["source_record_id"],
                        matter_dict["summary"],
                    ),
                )
                self._upsert_tasks(cur, tasks)
                self._upsert_approvals(cur, approvals)
                self._upsert_documents(cur, document_versions)
            conn.commit()
        matter_dict["tasks"] = tasks
        matter_dict["approvals"] = approvals
        matter_dict["document_versions"] = document_versions
        return matter_dict

    def append_matter_artifacts(
        self,
        matter_id: str,
        tasks: list[dict[str, Any]],
        approvals: list[dict[str, Any]],
        document_versions: list[dict[str, Any]],
        status: str,
        updated_at: str,
    ) -> dict[str, Any]:
        if not self.matter_exists(matter_id):
            raise LookupError("Matter not found.")
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE matters
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (updated_at, matter_id),
                )
                self._upsert_tasks(cur, tasks)
                self._upsert_approvals(cur, approvals)
                self._upsert_documents(cur, document_versions)
                self._recompute_matter_status(cur, matter_id, fallback_status=status, updated_at=updated_at)
            conn.commit()
        return self.get_matters_by_ids([matter_id])[0]

    def get_matters(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        created_at,
                        updated_at,
                        title,
                        client_name,
                        contact_email,
                        jurisdiction,
                        sector,
                        matter_type,
                        status,
                        source_record_type,
                        source_record_id,
                        summary
                    FROM matters
                    ORDER BY updated_at DESC
                    LIMIT 10
                    """
                )
                matter_rows = list(cur.fetchall())
        return self._hydrate_matter_rows(matter_rows)

    def get_matters_by_ids(self, matter_ids: list[str]) -> list[dict[str, Any]]:
        if not matter_ids:
            return []
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        created_at,
                        updated_at,
                        title,
                        client_name,
                        contact_email,
                        jurisdiction,
                        sector,
                        matter_type,
                        status,
                        source_record_type,
                        source_record_id,
                        summary
                    FROM matters
                    WHERE id = ANY(%s::uuid[])
                    ORDER BY updated_at DESC
                    """,
                    (matter_ids,),
                )
                matter_rows = list(cur.fetchall())
        return self._hydrate_matter_rows(matter_rows)

    def matter_exists(self, matter_id: str) -> bool:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT EXISTS (SELECT 1 FROM matters WHERE id = %s)", (matter_id,))
                return bool(cur.fetchone()[0])

    def sync_answer_review(self, reviewed_draft: dict[str, Any]) -> None:
        matter_id = reviewed_draft.get("matter_id")
        if not matter_id:
            return
        source_record_id = str(reviewed_draft["id"])
        reviewed_at = reviewed_draft.get("reviewed_at") or datetime.now(timezone.utc).isoformat()
        task_status = "completed" if reviewed_draft["review_status"] == "approved_for_use" else "blocked"
        document_status = _document_status_from_review(reviewed_draft["review_status"])
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE matters
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (reviewed_at, matter_id),
                )
                cur.execute(
                    """
                    UPDATE matter_tasks
                    SET status = %s,
                        updated_at = %s
                    WHERE matter_id = %s
                      AND source_record_id = %s
                    """,
                    (task_status, reviewed_at, matter_id, source_record_id),
                )
                cur.execute(
                    """
                    UPDATE matter_approvals
                    SET status = %s,
                        reviewer_name = %s,
                        notes = %s,
                        decided_at = %s
                    WHERE matter_id = %s
                      AND artifact_type = 'legal_answer'
                      AND artifact_id = %s
                    """,
                    (
                        reviewed_draft["review_status"],
                        reviewed_draft.get("reviewer_name"),
                        reviewed_draft.get("review_notes"),
                        reviewed_at,
                        matter_id,
                        source_record_id,
                    ),
                )
                cur.execute(
                    """
                    UPDATE document_versions
                    SET status = %s,
                        updated_at = %s
                    WHERE matter_id = %s
                      AND source_record_id = %s
                    """,
                    (document_status, reviewed_at, matter_id, source_record_id),
                )
                self._recompute_matter_status(
                    cur,
                    matter_id,
                    fallback_status=str(reviewed_draft["review_status"]),
                    updated_at=str(reviewed_at),
                )
            conn.commit()

    def list_sources(self, jurisdiction: str | None = None) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT title, issuer, jurisdiction, area, usage_note, production_ready
                    FROM legal_sources
                    WHERE jurisdiction = %s
                    ORDER BY area, title
                    """,
                    (active_jurisdiction,),
                )
                return self._normalize_rows(list(cur.fetchall()))

    def search_sources(
        self,
        query: str,
        limit: int = 5,
        jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        embedding = self._query_embedding(query, jurisdiction=active_jurisdiction)
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        title,
                        issuer,
                        jurisdiction,
                        area,
                        usage_note,
                        production_ready,
                        ROUND(CAST(1 - (embedding <=> %s::vector) AS numeric), 4) AS similarity
                    FROM legal_sources
                    WHERE jurisdiction = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, active_jurisdiction, embedding, limit),
                )
                rows = list(cur.fetchall())
                return self._normalize_rows(rows)

    def ingest_source_documents(self, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        parsed_documents = [
            document if isinstance(document, SourceDocument) else build_source_document(document)
            for document in (documents or [item.to_dict() for item in SEED_SOURCE_DOCUMENTS])
        ]
        chunk_count = 0
        backend_name = get_embedding_backend_name()

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                for document in parsed_documents:
                    current_hash = content_hash(document.body_text)
                    cur.execute(
                        """
                        SELECT id, content_hash, embedding_backend
                        FROM source_documents
                        WHERE source_key = %s
                        """,
                        (document.source_key,),
                    )
                    existing = cur.fetchone()

                    cur.execute(
                        """
                        INSERT INTO source_documents (
                            source_key,
                            title,
                            issuer,
                            jurisdiction,
                            area,
                            citation_label,
                            canonical_url,
                            body_text,
                            content_hash,
                            embedding_backend,
                            production_ready
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source_key) DO UPDATE
                        SET title = EXCLUDED.title,
                            issuer = EXCLUDED.issuer,
                            jurisdiction = EXCLUDED.jurisdiction,
                            area = EXCLUDED.area,
                            citation_label = EXCLUDED.citation_label,
                            canonical_url = EXCLUDED.canonical_url,
                            body_text = EXCLUDED.body_text,
                            content_hash = EXCLUDED.content_hash,
                            embedding_backend = EXCLUDED.embedding_backend,
                            production_ready = EXCLUDED.production_ready,
                            updated_at = NOW()
                        RETURNING id
                        """,
                        (
                            document.source_key,
                            document.title,
                            document.issuer,
                            document.jurisdiction,
                            document.area,
                            document.citation_label,
                            document.canonical_url,
                            document.body_text,
                            current_hash,
                            backend_name,
                            document.production_ready,
                        ),
                    )
                    source_document_id = cur.fetchone()["id"]

                    needs_reindex = (
                        existing is None
                        or existing["content_hash"] != current_hash
                        or existing["embedding_backend"] != backend_name
                    )
                    if not needs_reindex:
                        continue

                    cur.execute(
                        "DELETE FROM source_chunks WHERE source_document_id = %s",
                        (source_document_id,),
                    )
                    chunks = chunk_text(document.body_text)
                    embeddings = embed_texts(chunks)
                    for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
                        cur.execute(
                            """
                            INSERT INTO source_chunks (
                                source_document_id,
                                chunk_index,
                                citation_label,
                                content,
                                token_count,
                                embedding
                            )
                            VALUES (%s, %s, %s, %s, %s, %s::vector)
                            """,
                            (
                                source_document_id,
                                chunk_index,
                                document.citation_label,
                                chunk,
                                len(chunk.split()),
                                vector_literal(embedding),
                            ),
                        )
                    chunk_count += len(chunks)
            conn.commit()

        return {
            "documents": len(parsed_documents),
            "chunks": chunk_count,
            "embedding_backend": backend_name,
        }

    def search_citations(
        self,
        query: str,
        limit: int = 5,
        jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        active_jurisdiction = normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION)
        embedding = self._query_embedding(query, jurisdiction=active_jurisdiction)
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        source_documents.title,
                        source_documents.issuer,
                        source_documents.area,
                        source_documents.jurisdiction,
                        source_documents.citation_label,
                        source_documents.canonical_url,
                        source_documents.production_ready,
                        source_chunks.content AS snippet,
                        ROUND(CAST(1 - (source_chunks.embedding <=> %s::vector) AS numeric), 4) AS similarity
                    FROM source_chunks
                    JOIN source_documents
                        ON source_documents.id = source_chunks.source_document_id
                    WHERE source_documents.jurisdiction = %s
                    ORDER BY source_chunks.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, active_jurisdiction, embedding, limit),
                )
                rows = list(cur.fetchall())
                return self._normalize_rows(rows)

    # ── Auth (Postgres) ────────────────────────────────────────────────────────

    def save_user(self, record: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO lp_users (id, email, display_name, role, password_hash, salt, is_active, created_at, matter_ids)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (email) DO UPDATE
                    SET display_name=EXCLUDED.display_name, role=EXCLUDED.role,
                        password_hash=EXCLUDED.password_hash, salt=EXCLUDED.salt,
                        is_active=EXCLUDED.is_active, matter_ids=EXCLUDED.matter_ids
                    """,
                    (record["id"], record["email"], record["display_name"], record["role"],
                     record["password_hash"], record["salt"], record["is_active"],
                     record["created_at"], json.dumps(record.get("matter_ids", []))),
                )
            conn.commit()

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_users WHERE email = %s", (email.lower(),))
                return cur.fetchone()

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_users WHERE id = %s", (user_id,))
                return cur.fetchone()

    def list_users(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_users ORDER BY created_at DESC")
                return list(cur.fetchall())

    def save_session(self, session: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO lp_sessions (token, user_id, role, expires_at, created_at)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (token) DO NOTHING""",
                    (session["token"], session["user_id"], session["role"],
                     session["expires_at"], session["created_at"]),
                )
            conn.commit()

    def get_session(self, token: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_sessions WHERE token = %s", (token,))
                return cur.fetchone()

    def delete_session(self, token: str) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lp_sessions WHERE token = %s", (token,))
            conn.commit()

    def update_user_matter_ids(self, user_id: str, matter_id: str) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE lp_users SET matter_ids = matter_ids || %s::jsonb WHERE id = %s",
                    (json.dumps([matter_id]), user_id),
                )
            conn.commit()

    # ── Billing (Postgres) ─────────────────────────────────────────────────────

    def save_billing_record(self, record: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO lp_billing_records
                       (id, user_id, matter_id, service_tier, billing_type, amount_ngn, status, description, created_at, updated_at, period_start, period_end)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (record["id"], record["user_id"], record.get("matter_id"),
                     record["service_tier"], record["billing_type"], record["amount_ngn"],
                     record["status"], record["description"], record["created_at"],
                     record["updated_at"], record.get("period_start"), record.get("period_end")),
                )
            conn.commit()

    def save_subscription(self, record: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO lp_subscriptions (id, user_id, tier, seat_count, status, started_at, next_billing_at, cancelled_at, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, cancelled_at=EXCLUDED.cancelled_at""",
                    (record["id"], record["user_id"], record["tier"], record["seat_count"],
                     record["status"], record["started_at"], record.get("next_billing_at"),
                     record.get("cancelled_at"), record["created_at"]),
                )
            conn.commit()

    def get_subscription_by_user(self, user_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_subscriptions WHERE user_id=%s AND status='active' ORDER BY created_at DESC LIMIT 1", (user_id,))
                return cur.fetchone()

    def cancel_subscription(self, user_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE lp_subscriptions SET status='cancelled', cancelled_at=NOW() WHERE user_id=%s AND status='active' RETURNING *",
                    (user_id,),
                )
                row = cur.fetchone()
            conn.commit()
        return row

    def get_billing_records(self, user_id: str) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_billing_records WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
                return self._normalize_rows(list(cur.fetchall()))

    # ── Compliance (Postgres) ──────────────────────────────────────────────────

    def save_compliance_obligations(self, matter_id: str, obligations: list[dict[str, Any]]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lp_compliance_obligations WHERE matter_id = %s", (matter_id,))
                for ob in obligations:
                    cur.execute(
                        """INSERT INTO lp_compliance_obligations
                           (id, matter_id, obligation_type, description, due_date, status, recurrence, alert_sent, created_at, updated_at, completed_at, notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (ob["id"], ob["matter_id"], ob["obligation_type"], ob["description"],
                         ob["due_date"], ob["status"], ob["recurrence"], ob["alert_sent"],
                         ob["created_at"], ob["updated_at"], ob.get("completed_at"), ob.get("notes")),
                    )
            conn.commit()

    def get_compliance_obligations(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if matter_id:
                    cur.execute("SELECT * FROM lp_compliance_obligations WHERE matter_id=%s ORDER BY due_date", (matter_id,))
                else:
                    cur.execute("SELECT * FROM lp_compliance_obligations ORDER BY due_date")
                return self._normalize_rows(list(cur.fetchall()))

    def update_compliance_obligation(self, obligation_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join(f"{k}=%s" for k in updates)
                cur.execute(
                    f"UPDATE lp_compliance_obligations SET {set_clause} WHERE id=%s RETURNING *",
                    [*updates.values(), obligation_id],
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            raise LookupError("Compliance obligation not found.")
        return self._normalize_rows([row])[0]

    # ── Generated documents (Postgres) ────────────────────────────────────────

    def save_generated_document(self, doc: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO lp_generated_documents
                       (id, matter_id, template_key, title, body_text, status, generated_at, version_number, approved_by_user_id, approved_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (doc["id"], doc["matter_id"], doc["template_key"], doc["title"],
                     doc["body_text"], doc["status"], doc["generated_at"], doc["version_number"],
                     doc.get("approved_by_user_id"), doc.get("approved_at")),
                )
            conn.commit()

    def get_generated_documents(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if matter_id:
                    cur.execute("SELECT * FROM lp_generated_documents WHERE matter_id=%s ORDER BY generated_at DESC", (matter_id,))
                else:
                    cur.execute("SELECT * FROM lp_generated_documents ORDER BY generated_at DESC LIMIT 20")
                return self._normalize_rows(list(cur.fetchall()))

    def get_generated_document(self, doc_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_generated_documents WHERE id=%s", (doc_id,))
                row = cur.fetchone()
        return self._normalize_rows([row])[0] if row else None

    def update_generated_document(self, doc_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                set_clause = ", ".join(f"{k}=%s" for k in updates)
                cur.execute(f"UPDATE lp_generated_documents SET {set_clause} WHERE id=%s RETURNING *", [*updates.values(), doc_id])
                row = cur.fetchone()
            conn.commit()
        if row is None:
            raise LookupError("Generated document not found.")
        return self._normalize_rows([row])[0]

    # ── Contract reviews (Postgres) ────────────────────────────────────────────

    def save_contract_review(self, record: dict[str, Any]) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO lp_contract_reviews
                       (id, matter_id, submitted_by_user_id, filename, raw_text, status, ai_summary, extracted_clauses, risk_flags, lawyer_annotations, assigned_lawyer_id, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s)""",
                    (record["id"], record["matter_id"], record.get("submitted_by_user_id"),
                     record["filename"], record["raw_text"], record["status"], record["ai_summary"],
                     json.dumps(record.get("extracted_clauses", {})),
                     json.dumps(record.get("risk_flags", [])),
                     json.dumps(record.get("lawyer_annotations", [])),
                     record.get("assigned_lawyer_id"), record["created_at"], record["updated_at"]),
                )
            conn.commit()

    def get_contract_reviews(self, matter_id: str | None = None) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if matter_id:
                    cur.execute("SELECT id,matter_id,submitted_by_user_id,filename,status,ai_summary,extracted_clauses,risk_flags,lawyer_annotations,assigned_lawyer_id,created_at,updated_at FROM lp_contract_reviews WHERE matter_id=%s ORDER BY created_at DESC", (matter_id,))
                else:
                    cur.execute("SELECT id,matter_id,submitted_by_user_id,filename,status,ai_summary,extracted_clauses,risk_flags,lawyer_annotations,assigned_lawyer_id,created_at,updated_at FROM lp_contract_reviews ORDER BY created_at DESC LIMIT 20")
                return self._normalize_rows(list(cur.fetchall()))

    def get_contract_review(self, review_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM lp_contract_reviews WHERE id=%s", (review_id,))
                row = cur.fetchone()
        return self._normalize_rows([row])[0] if row else None

    def update_contract_review(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                jsonb_keys = {"extracted_clauses", "risk_flags", "lawyer_annotations"}
                parts, vals = [], []
                for k, v in updates.items():
                    if k in jsonb_keys:
                        parts.append(f"{k}=%s::jsonb")
                        vals.append(json.dumps(v))
                    else:
                        parts.append(f"{k}=%s")
                        vals.append(v)
                cur.execute(f"UPDATE lp_contract_reviews SET {', '.join(parts)} WHERE id=%s RETURNING *", [*vals, review_id])
                row = cur.fetchone()
            conn.commit()
        if row is None:
            raise LookupError("Contract review not found.")
        return self._normalize_rows([row])[0]

    def _upsert_tasks(self, cur: psycopg.Cursor, tasks: list[dict[str, Any]]) -> None:
        for task in tasks:
            cur.execute(
                """
                INSERT INTO matter_tasks (
                    id,
                    matter_id,
                    source_record_id,
                    title,
                    owner,
                    status,
                    risk_level,
                    rationale,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET source_record_id = EXCLUDED.source_record_id,
                    title = EXCLUDED.title,
                    owner = EXCLUDED.owner,
                    status = EXCLUDED.status,
                    risk_level = EXCLUDED.risk_level,
                    rationale = EXCLUDED.rationale,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    task["id"],
                    task["matter_id"],
                    task.get("source_record_id"),
                    task["title"],
                    task["owner"],
                    task["status"],
                    task["risk_level"],
                    task["rationale"],
                    task["created_at"],
                    task["updated_at"],
                ),
            )

    def _upsert_approvals(self, cur: psycopg.Cursor, approvals: list[dict[str, Any]]) -> None:
        for approval in approvals:
            cur.execute(
                """
                INSERT INTO matter_approvals (
                    id,
                    matter_id,
                    artifact_type,
                    artifact_id,
                    title,
                    status,
                    requested_role,
                    requested_at,
                    reviewer_name,
                    notes,
                    decided_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET artifact_type = EXCLUDED.artifact_type,
                    artifact_id = EXCLUDED.artifact_id,
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    requested_role = EXCLUDED.requested_role,
                    reviewer_name = EXCLUDED.reviewer_name,
                    notes = EXCLUDED.notes,
                    decided_at = EXCLUDED.decided_at
                """,
                (
                    approval["id"],
                    approval["matter_id"],
                    approval["artifact_type"],
                    approval["artifact_id"],
                    approval["title"],
                    approval["status"],
                    approval["requested_role"],
                    approval["requested_at"],
                    approval.get("reviewer_name"),
                    approval.get("notes"),
                    approval.get("decided_at"),
                ),
            )

    def _upsert_documents(self, cur: psycopg.Cursor, document_versions: list[dict[str, Any]]) -> None:
        for document in document_versions:
            cur.execute(
                """
                INSERT INTO document_versions (
                    id,
                    matter_id,
                    title,
                    document_type,
                    source_record_id,
                    version_number,
                    status,
                    summary,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET title = EXCLUDED.title,
                    document_type = EXCLUDED.document_type,
                    source_record_id = EXCLUDED.source_record_id,
                    version_number = EXCLUDED.version_number,
                    status = EXCLUDED.status,
                    summary = EXCLUDED.summary,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    document["id"],
                    document["matter_id"],
                    document["title"],
                    document["document_type"],
                    document["source_record_id"],
                    document["version_number"],
                    document["status"],
                    document["summary"],
                    document["created_at"],
                    document["updated_at"],
                ),
            )

    def _hydrate_matter_rows(self, matter_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not matter_rows:
            return []
        matter_ids = [str(row["id"]) for row in matter_rows]
        matter_map = {
            str(row["id"]): {
                **row,
                "tasks": [],
                "approvals": [],
                "document_versions": [],
            }
            for row in matter_rows
        }

        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        matter_id,
                        source_record_id,
                        title,
                        owner,
                        status,
                        risk_level,
                        rationale,
                        created_at,
                        updated_at
                    FROM matter_tasks
                    WHERE matter_id = ANY(%s::uuid[])
                    ORDER BY created_at ASC
                    """,
                    (matter_ids,),
                )
                for task in cur.fetchall():
                    matter_map[str(task["matter_id"])]["tasks"].append(task)

                cur.execute(
                    """
                    SELECT
                        id,
                        matter_id,
                        artifact_type,
                        artifact_id,
                        title,
                        status,
                        requested_role,
                        requested_at,
                        reviewer_name,
                        notes,
                        decided_at
                    FROM matter_approvals
                    WHERE matter_id = ANY(%s::uuid[])
                    ORDER BY requested_at ASC
                    """,
                    (matter_ids,),
                )
                for approval in cur.fetchall():
                    matter_map[str(approval["matter_id"])]["approvals"].append(approval)

                cur.execute(
                    """
                    SELECT
                        id,
                        matter_id,
                        title,
                        document_type,
                        source_record_id,
                        version_number,
                        status,
                        summary,
                        created_at,
                        updated_at
                    FROM document_versions
                    WHERE matter_id = ANY(%s::uuid[])
                    ORDER BY created_at ASC
                    """,
                    (matter_ids,),
                )
                for document in cur.fetchall():
                    matter_map[str(document["matter_id"])]["document_versions"].append(document)

        ordered = [matter_map[str(row["id"])] for row in matter_rows]
        return self._normalize_rows(ordered)

    def _recompute_matter_status(
        self,
        cur: psycopg.Cursor,
        matter_id: str | UUID,
        fallback_status: str,
        updated_at: str,
    ) -> str:
        cur.execute(
            """
            SELECT status
            FROM matter_approvals
            WHERE matter_id = %s
            """,
            (matter_id,),
        )
        approval_statuses = [row[0] for row in cur.fetchall()]
        overall_status = derive_matter_status(approval_statuses) if approval_statuses else fallback_status
        cur.execute(
            """
            UPDATE matters
            SET status = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (overall_status, updated_at, matter_id),
        )
        return overall_status

    def _normalize_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from datetime import date as _date, datetime as _datetime
        import uuid as _uuid
        def _coerce(v: Any) -> Any:
            if isinstance(v, _datetime):
                return v.isoformat()
            if isinstance(v, _date):
                return v.isoformat()
            if isinstance(v, _uuid.UUID):
                return str(v)
            if isinstance(v, Decimal):
                return float(v)
            return v
        for row in rows:
            for key, value in list(row.items()):
                row[key] = _coerce(value)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            for nested_key, nested_value in list(item.items()):
                                item[nested_key] = _coerce(nested_value)
            if "jurisdiction" in row and not row["jurisdiction"]:
                row["jurisdiction"] = DEFAULT_JURISDICTION
        return rows

    def _source_embedding(self, source: LegalSource) -> str:
        text = " ".join([source.jurisdiction, source.title, source.issuer, source.area, source.usage_note])
        return vector_literal(embed_text(text))

    def _query_embedding(
        self,
        query: str,
        sector: str | None = None,
        jurisdiction: str | None = None,
    ) -> str:
        parts = [normalize_jurisdiction(jurisdiction or DEFAULT_JURISDICTION), query]
        if sector:
            parts.append(sector)
        text = " ".join(parts)
        return vector_literal(embed_text(text))


def _backend_name() -> str:
    explicit = os.getenv("APP_STORAGE_BACKEND")
    if explicit:
        return explicit.strip().lower()
    if os.getenv("DATABASE_URL"):
        return "postgres"
    return "json"


@lru_cache(maxsize=1)
def get_backend() -> JsonStorageBackend | PostgresStorageBackend:
    backend_name = _backend_name()
    if backend_name == "postgres":
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when APP_STORAGE_BACKEND=postgres.")
        return PostgresStorageBackend(database_url)
    return JsonStorageBackend()


def _document_status_from_review(review_status: str) -> str:
    if review_status == "approved_for_use":
        return "approved"
    if review_status == "rejected_by_lawyer":
        return "rejected"
    return "draft"


def _normalize_legal_source(source: dict[str, Any]) -> dict[str, Any]:
    source.setdefault("jurisdiction", DEFAULT_JURISDICTION)
    return source


def _normalize_intake_record(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("jurisdiction", DEFAULT_JURISDICTION)
    if isinstance(record.get("sources"), list):
        record["sources"] = [_normalize_legal_source(source) for source in record["sources"]]
    return record


def _normalize_matter_record(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("jurisdiction", DEFAULT_JURISDICTION)
    return record


def _normalize_answer_draft(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("jurisdiction", DEFAULT_JURISDICTION)
    return record


def initialize_storage() -> None:
    get_backend().initialize()


def get_storage_backend_name() -> str:
    return get_backend().name


def save_intake(record: IntakeRecord) -> None:
    get_backend().save_intake(record)


def get_intakes() -> list[dict[str, Any]]:
    return get_backend().get_intakes()


def enqueue_review(record: IntakeRecord) -> None:
    get_backend().enqueue_review(record)


def get_review_queue() -> list[dict[str, Any]]:
    return get_backend().get_review_queue()


def save_answer_draft(draft: dict[str, Any]) -> None:
    get_backend().save_answer_draft(draft)


def get_answer_drafts() -> list[dict[str, Any]]:
    return get_backend().get_answer_drafts()


def review_answer_draft(
    draft_id: str,
    review_status: str,
    reviewer_name: str,
    review_notes: str | None = None,
) -> dict[str, Any]:
    return get_backend().review_answer_draft(
        draft_id,
        review_status=review_status,
        reviewer_name=reviewer_name,
        review_notes=review_notes,
    )


def upsert_matter(matter: MatterRecord | dict[str, Any]) -> dict[str, Any]:
    return get_backend().upsert_matter(matter)


def append_matter_artifacts(
    matter_id: str,
    tasks: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    document_versions: list[dict[str, Any]],
    status: str,
    updated_at: str,
) -> dict[str, Any]:
    return get_backend().append_matter_artifacts(
        matter_id,
        tasks=tasks,
        approvals=approvals,
        document_versions=document_versions,
        status=status,
        updated_at=updated_at,
    )


def get_matters() -> list[dict[str, Any]]:
    return get_backend().get_matters()


def matter_exists(matter_id: str) -> bool:
    return get_backend().matter_exists(matter_id)


def sync_answer_review(reviewed_draft: dict[str, Any]) -> None:
    return get_backend().sync_answer_review(reviewed_draft)


def list_sources(jurisdiction: str | None = None) -> list[dict[str, Any]]:
    return get_backend().list_sources(jurisdiction=jurisdiction)


def search_sources(
    query: str,
    limit: int = 5,
    jurisdiction: str | None = None,
) -> list[dict[str, Any]]:
    return get_backend().search_sources(query, limit=limit, jurisdiction=jurisdiction)


def ingest_source_documents(documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return get_backend().ingest_source_documents(documents)


def search_citations(
    query: str,
    limit: int = 5,
    jurisdiction: str | None = None,
) -> list[dict[str, Any]]:
    return get_backend().search_citations(query, limit=limit, jurisdiction=jurisdiction)


# ── New module-level delegates ──────────────────────────────────────────────────

def save_user(record: dict[str, Any]) -> None:
    get_backend().save_user(record)

def get_user_by_email(email: str) -> dict[str, Any] | None:
    return get_backend().get_user_by_email(email)

def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    return get_backend().get_user_by_id(user_id)

def list_users() -> list[dict[str, Any]]:
    return get_backend().list_users()

def save_session(session: dict[str, Any]) -> None:
    get_backend().save_session(session)

def get_session(token: str) -> dict[str, Any] | None:
    return get_backend().get_session(token)

def delete_session(token: str) -> None:
    get_backend().delete_session(token)

def update_user_matter_ids(user_id: str, matter_id: str) -> None:
    get_backend().update_user_matter_ids(user_id, matter_id)

def save_billing_record(record: dict[str, Any]) -> None:
    get_backend().save_billing_record(record)

def save_subscription(record: dict[str, Any]) -> None:
    get_backend().save_subscription(record)

def get_subscription_by_user(user_id: str) -> dict[str, Any] | None:
    return get_backend().get_subscription_by_user(user_id)

def cancel_subscription(user_id: str) -> dict[str, Any] | None:
    return get_backend().cancel_subscription(user_id)

def get_billing_records(user_id: str) -> list[dict[str, Any]]:
    return get_backend().get_billing_records(user_id)

def save_compliance_obligations(matter_id: str, obligations: list[dict[str, Any]]) -> None:
    get_backend().save_compliance_obligations(matter_id, obligations)

def get_compliance_obligations(matter_id: str | None = None) -> list[dict[str, Any]]:
    return get_backend().get_compliance_obligations(matter_id=matter_id)

def update_compliance_obligation(obligation_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    return get_backend().update_compliance_obligation(obligation_id, updates)

def save_generated_document(doc: dict[str, Any]) -> None:
    get_backend().save_generated_document(doc)

def get_generated_documents(matter_id: str | None = None) -> list[dict[str, Any]]:
    return get_backend().get_generated_documents(matter_id=matter_id)

def get_generated_document(doc_id: str) -> dict[str, Any] | None:
    return get_backend().get_generated_document(doc_id)

def update_generated_document(doc_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    return get_backend().update_generated_document(doc_id, updates)

def save_contract_review(record: dict[str, Any]) -> None:
    get_backend().save_contract_review(record)

def get_contract_reviews(matter_id: str | None = None) -> list[dict[str, Any]]:
    return get_backend().get_contract_reviews(matter_id=matter_id)

def get_contract_review(review_id: str) -> dict[str, Any] | None:
    return get_backend().get_contract_review(review_id)

def update_contract_review(review_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    return get_backend().update_contract_review(review_id, updates)
