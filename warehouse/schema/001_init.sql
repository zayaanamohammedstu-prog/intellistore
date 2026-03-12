-- =============================================================================
-- 001_init.sql – Core operational tables
-- Run this first against the target PostgreSQL database.
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    google_sub  VARCHAR(255) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    name        VARCHAR(255),
    picture     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users (google_sub);
CREATE INDEX IF NOT EXISTS idx_users_email      ON users (email);

-- ---------------------------------------------------------------------------
-- etl_jobs
-- ---------------------------------------------------------------------------
CREATE TYPE IF NOT EXISTS etl_job_status AS ENUM (
    'pending', 'running', 'completed', 'failed'
);

CREATE TABLE IF NOT EXISTS etl_jobs (
    id                UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID            NOT NULL REFERENCES users (id),
    original_filename VARCHAR(512)    NOT NULL,
    stored_path       TEXT            NOT NULL,
    status            etl_job_status  NOT NULL DEFAULT 'pending',
    error_message     TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_etl_jobs_user_id ON etl_jobs (user_id);
CREATE INDEX IF NOT EXISTS idx_etl_jobs_status  ON etl_jobs (status);

-- ---------------------------------------------------------------------------
-- staging_sales_raw  (landing zone – raw rows from uploaded files)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging_sales_raw (
    id          BIGSERIAL   PRIMARY KEY,
    job_id      UUID        NOT NULL REFERENCES etl_jobs (id),
    row_number  INTEGER     NOT NULL,
    data        JSONB       NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_sales_raw_job_id ON staging_sales_raw (job_id);
