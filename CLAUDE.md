# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Law Firm OS — a Nigeria-first legal operations platform that automates founder intake, workflow generation, document briefing, and lawyer review queues. This is a draft operational guidance system (not a legal advice provider); mandatory lawyer review gates are a core safety requirement.

## Commands

**Run locally (JSON storage, no dependencies needed):**
```bash
python3 server.py
# Opens at http://127.0.0.1:8000
```

**Run with PostgreSQL + OpenAI:**
```bash
docker compose up -d db
export APP_STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://lexpilot:lexpilot@127.0.0.1:5432/lexpilot
export OPENAI_API_KEY=sk-...
python3 server.py
```

**Run all tests:**
```bash
python3 -m unittest discover -s tests
```

**Run a single test:**
```bash
python3 -m unittest tests.test_workflows
python3 -m unittest tests.test_workflows.TestWorkflows.test_regulated_sector_triggers_lawyer_review
```

No build step, no package manager — pure Python standard library.

## Architecture

### Request Flow

```
HTTP Request → server.py (ThreadingHTTPServer)
                    ↓
           legal_mvp/ business logic
           ├── workflows.py  — rule-based workflow generation
           ├── matters.py    — matter lifecycle management
           ├── answers.py    — OpenAI Structured Outputs integration
           ├── embeddings.py — OpenAI or local hash fallback
           └── storage.py    — adapter pattern (JSON ↔ Postgres)
                    ↓
           static/ (vanilla JS SPA served by server.py)
```

### Pluggable Storage (`legal_mvp/storage.py`)

Two backends selected via `APP_STORAGE_BACKEND` env var:
- **JSON** (default): Files in `data/` — works offline, no dependencies
- **PostgreSQL**: pgvector for semantic search on source chunks; schema in `sql/001_init_pgvector.sql`

Storage is initialized once at server startup. All endpoints use the same backend instance.

### Pluggable Embeddings (`legal_mvp/embeddings.py`)

- **OpenAI** (`text-embedding-3-small`): Used when `OPENAI_API_KEY` is set
- **Local hash fallback**: Deterministic but non-semantic — system runs fully offline without API keys

### Domain Model

**Matter** is the aggregate root. Each intake creates a matter, which tracks:
- `IntakeRecord` → intake form submission
- `WorkflowStep[]` → generated tasks with owners and risk flags
- `AnswerDraft[]` → LLM-generated answers with review status
- `MatterApproval[]` → lawyer sign-offs
- `DocumentVersion[]` — generated document drafts

### Lawyer Review Escalation

Regulated sectors auto-escalate to lawyer review in `legal_mvp/workflows.py`. Sectors that trigger escalation: fintech, health, education, energy, logistics. This is a hard safety boundary — do not remove or relax escalation logic without explicit instruction.

### Jurisdiction System (`legal_mvp/jurisdictions.py`)

Currently Nigeria-only. Designed for future "jurisdiction packs" for other African countries. Jurisdiction selection affects which sources and workflow rules apply.

## Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_STORAGE_BACKEND` | `json` | `json` or `postgres` |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | — | Enables OpenAI answers + embeddings |
| `OPENAI_ANSWER_MODEL` | `gpt-5-mini` | LLM for answer generation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` | Must match pgvector column size |

## API Endpoints

All served from `server.py`. GET endpoints return JSON; POST bodies are JSON.

- `GET /api/health` — server status, storage backend, launch jurisdiction
- `GET /api/intakes` — last 10 intakes
- `GET /api/matters` — last 10 matters (with tasks/approvals/documents)
- `GET /api/answer-drafts` — last 10 generated answers
- `GET /api/review-queue` — pending lawyer review items
- `GET /api/sources` — available legal sources for jurisdiction
- `GET /api/citation-search?q=` — semantic search on source chunks
- `POST /api/intakes` — create intake → enqueue review → create matter
- `POST /api/legal-answer` — generate answer (optionally attached to matter)
- `POST /api/answer-drafts/:id/review` — lawyer approve/reject answer
- `POST /api/source-documents/ingest` — upload new legal sources
