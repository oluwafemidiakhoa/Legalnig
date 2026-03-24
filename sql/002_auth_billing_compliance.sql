-- Migration 002: Auth, Billing, Compliance, Documents, Contracts
-- Prefixed with lp_ to avoid conflicts with any existing tables

-- Users and sessions
CREATE TABLE IF NOT EXISTS lp_users (
    id          uuid PRIMARY KEY,
    email       text NOT NULL UNIQUE,
    display_name text NOT NULL,
    role        text NOT NULL CHECK (role IN ('sme_founder', 'lawyer', 'admin')),
    password_hash text NOT NULL,
    salt        text NOT NULL,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT NOW(),
    matter_ids  jsonb NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS lp_sessions (
    token       text PRIMARY KEY,
    user_id     uuid NOT NULL REFERENCES lp_users(id) ON DELETE CASCADE,
    role        text NOT NULL,
    expires_at  timestamptz NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lp_sessions_user_idx ON lp_sessions(user_id);
CREATE INDEX IF NOT EXISTS lp_sessions_expires_idx ON lp_sessions(expires_at);

-- Billing
CREATE TABLE IF NOT EXISTS lp_billing_records (
    id           uuid PRIMARY KEY,
    user_id      uuid NOT NULL REFERENCES lp_users(id),
    matter_id    uuid REFERENCES matters(id) ON DELETE SET NULL,
    service_tier text NOT NULL,
    billing_type text NOT NULL,
    amount_ngn   numeric(14,2) NOT NULL,
    status       text NOT NULL,
    description  text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT NOW(),
    updated_at   timestamptz NOT NULL DEFAULT NOW(),
    period_start timestamptz,
    period_end   timestamptz
);

CREATE INDEX IF NOT EXISTS lp_billing_user_idx ON lp_billing_records(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS lp_subscriptions (
    id              uuid PRIMARY KEY,
    user_id         uuid NOT NULL REFERENCES lp_users(id),
    tier            text NOT NULL,
    seat_count      integer NOT NULL DEFAULT 1,
    status          text NOT NULL,
    started_at      timestamptz NOT NULL,
    next_billing_at timestamptz,
    cancelled_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lp_subscriptions_user_idx ON lp_subscriptions(user_id, status);

-- Compliance calendar
CREATE TABLE IF NOT EXISTS lp_compliance_obligations (
    id               uuid PRIMARY KEY,
    matter_id        uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    obligation_type  text NOT NULL,
    description      text NOT NULL,
    due_date         date NOT NULL,
    status           text NOT NULL DEFAULT 'upcoming',
    recurrence       text NOT NULL,
    alert_sent       boolean NOT NULL DEFAULT false,
    created_at       timestamptz NOT NULL DEFAULT NOW(),
    updated_at       timestamptz NOT NULL DEFAULT NOW(),
    completed_at     timestamptz,
    notes            text
);

CREATE INDEX IF NOT EXISTS lp_compliance_matter_idx ON lp_compliance_obligations(matter_id, due_date);
CREATE INDEX IF NOT EXISTS lp_compliance_due_idx ON lp_compliance_obligations(due_date, status);

-- Generated documents
CREATE TABLE IF NOT EXISTS lp_generated_documents (
    id                   uuid PRIMARY KEY,
    matter_id            uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    template_key         text NOT NULL,
    title                text NOT NULL,
    body_text            text NOT NULL,
    status               text NOT NULL DEFAULT 'draft',
    generated_at         timestamptz NOT NULL DEFAULT NOW(),
    version_number       integer NOT NULL DEFAULT 1,
    approved_by_user_id  uuid REFERENCES lp_users(id),
    approved_at          timestamptz
);

CREATE INDEX IF NOT EXISTS lp_gendocs_matter_idx ON lp_generated_documents(matter_id, generated_at DESC);

-- Contract reviews
CREATE TABLE IF NOT EXISTS lp_contract_reviews (
    id                    uuid PRIMARY KEY,
    matter_id             uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    submitted_by_user_id  uuid REFERENCES lp_users(id),
    filename              text NOT NULL,
    raw_text              text NOT NULL,
    status                text NOT NULL DEFAULT 'pending_ai_review',
    ai_summary            text NOT NULL DEFAULT '',
    extracted_clauses     jsonb NOT NULL DEFAULT '{}'::jsonb,
    risk_flags            jsonb NOT NULL DEFAULT '[]'::jsonb,
    lawyer_annotations    jsonb NOT NULL DEFAULT '[]'::jsonb,
    assigned_lawyer_id    uuid REFERENCES lp_users(id),
    created_at            timestamptz NOT NULL DEFAULT NOW(),
    updated_at            timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lp_contracts_matter_idx ON lp_contract_reviews(matter_id, created_at DESC);
CREATE INDEX IF NOT EXISTS lp_contracts_status_idx ON lp_contract_reviews(status);
