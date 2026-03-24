-- Migration 003: Answer cache + usage tracking
CREATE TABLE IF NOT EXISTS lp_answer_cache (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_hash text NOT NULL,
    jurisdiction  text NOT NULL DEFAULT 'nigeria',
    question_text text NOT NULL,
    answer_json   jsonb NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT NOW(),
    hit_count     integer NOT NULL DEFAULT 0,
    last_hit_at   timestamptz,
    UNIQUE (question_hash, jurisdiction)
);
CREATE INDEX IF NOT EXISTS lp_cache_hash_idx    ON lp_answer_cache(question_hash, jurisdiction);
CREATE INDEX IF NOT EXISTS lp_cache_created_idx ON lp_answer_cache(created_at);

CREATE TABLE IF NOT EXISTS lp_usage_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL,
    action_type text NOT NULL,
    tier        text NOT NULL DEFAULT 'free',
    matter_id   uuid,
    cache_hit   boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS lp_usage_user_day_idx   ON lp_usage_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS lp_usage_user_month_idx ON lp_usage_log(user_id, action_type, created_at DESC);

ALTER TABLE lp_billing_records ADD COLUMN IF NOT EXISTS credits_remaining integer NOT NULL DEFAULT 0;
