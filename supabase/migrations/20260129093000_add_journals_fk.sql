-- Ensure journals table and manuscripts.journal_id relationship exist

CREATE TABLE IF NOT EXISTS journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    issn TEXT,
    impact_factor FLOAT4,
    cover_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE manuscripts
    ADD COLUMN IF NOT EXISTS journal_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'manuscripts_journal_id_fkey'
    ) THEN
        ALTER TABLE manuscripts
            ADD CONSTRAINT manuscripts_journal_id_fkey
            FOREIGN KEY (journal_id)
            REFERENCES journals(id);
    END IF;
END $$;
