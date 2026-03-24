# AI Law Firm OS for Nigeria

AI Law Firm OS for Nigeria is a dependency-light scaffold for a Nigeria-first legal operations
platform. It is intentionally narrow: founder intake, workflow generation, document briefing,
matter tracking, lawyer review queue, and source-backed guidance placeholders. The expansion
path for other African countries is a jurisdiction-pack model, but this codebase now starts
explicitly with Nigeria as the active launch jurisdiction.

This project does not provide legal advice. It creates draft operational packets that should be
reviewed by a licensed Nigerian lawyer before any filing, client delivery, or formal opinion.

## Why this shape

- The repo was empty, so the scaffold optimizes for a runnable baseline instead of framework churn.
- The current MVP uses Python standard library only, which keeps local validation possible.
- The product boundary is deliberate: legal intake + workflow automation + lawyer escalation.

## Product boundaries

- Founder intake for a Nigerian legal/compliance workflow
- Draft compliance checklist generation
- Draft document brief generation
- Admin queue for lawyer review
- Placeholder source registry for counsel-curated Nigerian materials

## Project layout

```text
.
|-- docs/
|   `-- architecture.md
|-- legal_mvp/
|   |-- __init__.py
|   |-- answers.py
|   |-- ingestion.py
|   |-- matters.py
|   |-- models.py
|   |-- runtime_env.py
|   |-- source_corpus.py
|   |-- sources.py
|   |-- storage.py
|   `-- workflows.py
|-- static/
|   |-- app.js
|   |-- index.html
|   `-- styles.css
|-- tests/
|   `-- test_workflows.py
`-- server.py
```

## Run locally

```bash
python3 server.py
```

Then open `http://127.0.0.1:8000`.

By default the app falls back to JSON storage if `DATABASE_URL` is not set.

## Run with Postgres and pgvector

1. Start the database:

```bash
docker compose up -d db
```

2. Set the backend and connection string:

```bash
export APP_STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://lexpilot:lexpilot@127.0.0.1:5432/lexpilot
export OPENAI_API_KEY=your_key_here
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small
export OPENAI_EMBEDDING_DIMENSIONS=1536
export OPENAI_ANSWER_MODEL=gpt-5-mini
```

3. Start the app:

```bash
python3 server.py
```

The server bootstraps the schema in [`sql/001_init_pgvector.sql`](./sql/001_init_pgvector.sql)
and seeds the legal source registry automatically.

## pgvector and embeddings note

The vector path now supports two modes:

- If `OPENAI_API_KEY` is set, [`legal_mvp/embeddings.py`](./legal_mvp/embeddings.py) calls the
  OpenAI embeddings API.
- If no key is configured, the app falls back to a deterministic local hash embedder so the rest
  of the workflow still runs in development.

The seed citation corpus is defined in [`legal_mvp/source_corpus.py`](./legal_mvp/source_corpus.py)
and chunked through [`legal_mvp/ingestion.py`](./legal_mvp/ingestion.py).

The cited answer generation flow is implemented in [`legal_mvp/answers.py`](./legal_mvp/answers.py)
and uses OpenAI Structured Outputs through the Responses API. Answer drafts are persisted with
review metadata so a lawyer can approve or reject them inside the app before reuse.

Matter-system records now live alongside those drafts. Founder intake packets and cited answers
are attached to tracked matters with tasks, approvals, and document versions before they are shown
in the UI.

## Test locally

```bash
python3 -m unittest discover -s tests
```

## API surface

- `GET /api/health`
- `GET /api/answer-drafts`
- `GET /api/intakes`
- `GET /api/matters`
- `GET /api/review-queue`
- `GET /api/sources`
- `GET /api/citation-search?q=employment`
- `GET /api/source-search?q=employment`
- `POST /api/intakes`
- `POST /api/legal-answer`
- `POST /api/answer-drafts/:id/review`
- `POST /api/source-documents/ingest`

## Immediate next steps

1. Replace the seed corpus with counsel-approved statutes, regulations, cases, and filing guides.
2. Add metadata filters for jurisdiction, practice area, source type, and production readiness.
3. Add review actions for workflow-packet approvals so intake matters can move through the same state machine as cited answers.
4. Add authentication and role-based review permissions.
5. Introduce real document template rendering.
6. Integrate WhatsApp and payments once the core workflow is stable.
