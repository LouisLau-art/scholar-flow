-- Create types
CREATE TYPE doi_registration_status AS ENUM ('pending', 'submitting', 'registered', 'failed');
CREATE TYPE doi_task_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- DOI Registrations
CREATE TABLE doi_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,
    doi VARCHAR(255) UNIQUE,
    status doi_registration_status NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    crossref_batch_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- DOI Tasks
CREATE TABLE doi_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID NOT NULL REFERENCES doi_registrations(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    status doi_task_status NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(100),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 4,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Audit Log
CREATE TABLE doi_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID REFERENCES doi_registrations(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    request_payload JSONB,
    response_status INTEGER,
    response_body TEXT,
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Articles updates
ALTER TABLE articles ADD COLUMN IF NOT EXISTS doi VARCHAR(255) UNIQUE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS doi_registered_at TIMESTAMPTZ;

-- Indexes
CREATE INDEX idx_doi_tasks_pending ON doi_tasks (run_at ASC) WHERE status = 'pending';
CREATE INDEX idx_doi_tasks_stale ON doi_tasks (locked_at) WHERE status = 'processing';
CREATE INDEX idx_doi_registrations_article ON doi_registrations (article_id);
CREATE INDEX idx_doi_audit_log_registration ON doi_audit_log (registration_id, created_at DESC);
