# Architecture

## Intent

This scaffold models the first useful shape of a Nigerian legal operations product:

- collect structured intake,
- generate a bounded workflow packet,
- assemble document briefs,
- hand off complex work to a licensed lawyer,
- and keep all output clearly inside a draft-assistant boundary.

## Runtime

- Python standard library HTTP server
- JSON files for local persistence
- Static frontend served from the same process

This is not the target production architecture. It is the fastest validated baseline for an empty
repo with no dependency installation.

## Request flow

1. A founder submits an intake packet from the web UI.
2. The server validates consent and required fields.
3. Workflow generation creates a source-backed draft checklist.
4. Document briefing creates draft artifacts that need legal review.
5. A review queue entry is recorded for counsel or legal operations.
6. The frontend renders the generated packet and current review queue.

## Safety boundary

- The system produces draft workflows, not legal opinions.
- Every generated packet includes a disclaimer.
- High-risk sectors and edge cases are escalated to lawyer review.
- The source registry is a placeholder inventory, not a live legal database.

## Production path

The likely production version would evolve toward:

- Next.js or another typed web framework for the client
- FastAPI or a typed service layer for APIs
- Postgres plus `pgvector`
- object storage for document artifacts
- audit logs and access controls
- source ingestion pipelines
- human review controls before client-facing output

## Domain model

- `IntakeRequest`: founder and business facts
- `WorkflowStep`: a bounded next action with owner and risk level
- `DocumentBrief`: a draft artifact definition for later rendering
- `LegalSource`: a counseled source registry entry
- `IntakeRecord`: the full stored packet
