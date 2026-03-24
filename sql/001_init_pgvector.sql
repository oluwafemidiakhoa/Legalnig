CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS intakes (
    id uuid PRIMARY KEY,
    matter_id uuid,
    submitted_at timestamptz NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'Nigeria',
    founder_name text NOT NULL,
    business_name text NOT NULL,
    entity_type text NOT NULL,
    sector text NOT NULL,
    use_case text NOT NULL,
    contact_email text NOT NULL,
    consent boolean NOT NULL,
    status text NOT NULL,
    workflow jsonb NOT NULL,
    documents jsonb NOT NULL,
    sources jsonb NOT NULL,
    disclaimers jsonb NOT NULL,
    query_embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT NOW()
);

ALTER TABLE intakes
    ADD COLUMN IF NOT EXISTS matter_id uuid;

ALTER TABLE intakes
    ADD COLUMN IF NOT EXISTS jurisdiction text NOT NULL DEFAULT 'Nigeria';

CREATE TABLE IF NOT EXISTS review_queue (
    intake_id uuid PRIMARY KEY REFERENCES intakes(id) ON DELETE CASCADE,
    submitted_at timestamptz NOT NULL,
    business_name text NOT NULL,
    use_case text NOT NULL,
    sector text NOT NULL,
    status text NOT NULL,
    owner text NOT NULL DEFAULT 'lawyer_review'
);

CREATE TABLE IF NOT EXISTS legal_sources (
    id bigserial PRIMARY KEY,
    title text NOT NULL,
    issuer text NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'Nigeria',
    area text NOT NULL,
    usage_note text NOT NULL,
    production_ready boolean NOT NULL DEFAULT false,
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (title, area)
);

CREATE INDEX IF NOT EXISTS review_queue_submitted_at_idx
    ON review_queue (submitted_at DESC);

CREATE TABLE IF NOT EXISTS source_documents (
    id bigserial PRIMARY KEY,
    source_key text NOT NULL UNIQUE,
    title text NOT NULL,
    issuer text NOT NULL,
    jurisdiction text NOT NULL,
    area text NOT NULL,
    citation_label text NOT NULL,
    canonical_url text,
    body_text text NOT NULL,
    content_hash text NOT NULL,
    embedding_backend text NOT NULL DEFAULT 'local',
    production_ready boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id bigserial PRIMARY KEY,
    source_document_id bigint NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    citation_label text NOT NULL,
    content text NOT NULL,
    token_count integer NOT NULL DEFAULT 0,
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (source_document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS source_chunks_document_idx
    ON source_chunks (source_document_id, chunk_index);

CREATE INDEX IF NOT EXISTS source_chunks_embedding_hnsw_idx
    ON source_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS matters (
    id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    title text NOT NULL,
    client_name text NOT NULL,
    contact_email text NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'Nigeria',
    sector text NOT NULL,
    matter_type text NOT NULL,
    status text NOT NULL,
    source_record_type text NOT NULL,
    source_record_id text,
    summary text NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_tasks (
    id uuid PRIMARY KEY,
    matter_id uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    source_record_id text,
    title text NOT NULL,
    owner text NOT NULL,
    status text NOT NULL,
    risk_level text NOT NULL,
    rationale text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_approvals (
    id uuid PRIMARY KEY,
    matter_id uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    artifact_type text NOT NULL,
    artifact_id text NOT NULL,
    title text NOT NULL,
    status text NOT NULL,
    requested_role text NOT NULL,
    requested_at timestamptz NOT NULL,
    reviewer_name text,
    notes text,
    decided_at timestamptz
);

CREATE TABLE IF NOT EXISTS document_versions (
    id uuid PRIMARY KEY,
    matter_id uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    title text NOT NULL,
    document_type text NOT NULL,
    source_record_id text NOT NULL,
    version_number integer NOT NULL,
    status text NOT NULL,
    summary text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS matters_updated_at_idx
    ON matters (updated_at DESC);

CREATE INDEX IF NOT EXISTS matter_tasks_matter_idx
    ON matter_tasks (matter_id, created_at);

CREATE INDEX IF NOT EXISTS matter_approvals_matter_idx
    ON matter_approvals (matter_id, requested_at);

CREATE INDEX IF NOT EXISTS document_versions_matter_idx
    ON document_versions (matter_id, created_at);

CREATE TABLE IF NOT EXISTS answer_drafts (
    id uuid PRIMARY KEY,
    matter_id uuid REFERENCES matters(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'Nigeria',
    question text NOT NULL,
    status text NOT NULL,
    answer_text text NOT NULL,
    risk_level text NOT NULL,
    requires_lawyer_review boolean NOT NULL,
    recommended_actions jsonb NOT NULL,
    follow_up_questions jsonb NOT NULL,
    citations jsonb NOT NULL,
    model text NOT NULL,
    review_status text NOT NULL,
    reviewer_name text,
    review_notes text,
    reviewed_at timestamptz,
    disclaimer text NOT NULL
);

ALTER TABLE answer_drafts
    ADD COLUMN IF NOT EXISTS matter_id uuid REFERENCES matters(id) ON DELETE SET NULL;

ALTER TABLE answer_drafts
    ADD COLUMN IF NOT EXISTS reviewer_name text;

ALTER TABLE answer_drafts
    ADD COLUMN IF NOT EXISTS review_notes text;

ALTER TABLE answer_drafts
    ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;

ALTER TABLE legal_sources
    ADD COLUMN IF NOT EXISTS jurisdiction text NOT NULL DEFAULT 'Nigeria';

ALTER TABLE matters
    ADD COLUMN IF NOT EXISTS jurisdiction text NOT NULL DEFAULT 'Nigeria';

ALTER TABLE answer_drafts
    ADD COLUMN IF NOT EXISTS jurisdiction text NOT NULL DEFAULT 'Nigeria';

CREATE INDEX IF NOT EXISTS answer_drafts_created_at_idx
    ON answer_drafts (created_at DESC);
