-- 查重报告表
-- 包含 manuscript_id 唯一索引以防止重复任务
CREATE TABLE IF NOT EXISTS plagiarism_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE,
    external_id TEXT,
    similarity_score FLOAT4,
    report_url TEXT,
    status TEXT DEFAULT 'pending',
    retry_count INT2 DEFAULT 0,
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

