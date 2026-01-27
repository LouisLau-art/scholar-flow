-- ScholarFlow Database Schema (v1.4.0)
-- 包含财务幂等性约束与状态机定义

-- 1. 稿件表
CREATE TABLE manuscripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    abstract TEXT,
    file_path TEXT,
    author_id UUID REFERENCES auth.users(id),
    editor_id UUID REFERENCES auth.users(id),
    status TEXT DEFAULT 'draft',
    kpi_owner_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 审稿报告表
CREATE TABLE review_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES auth.users(id),
    token TEXT UNIQUE, -- 免登录 Token 唯一
    expiry_date TIMESTAMPTZ,
    status TEXT DEFAULT 'invited',
    content TEXT,
    score INTEGER CHECK (score >= 1 AND score <= 5),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 财务账单表 (实现幂等性)
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE, -- 确保一个稿件仅对应一个账单
    amount NUMERIC(10, 2) NOT NULL,
    pdf_url TEXT,
    status TEXT DEFAULT 'unpaid',
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 财务幂等性辅助：防止重复确认的逻辑由业务层状态机保证，
    -- 这里通过 manuscript_id 的 UNIQUE 约束确保账单生成的幂等。
    CONSTRAINT unique_manuscript_invoice UNIQUE (manuscript_id)
);

-- 4. KPI 统计辅助视图
CREATE VIEW editor_kpi_stats AS
SELECT 
    kpi_owner_id,
    COUNT(*) as processed_count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_process_hours
FROM manuscripts
WHERE status != 'draft'
GROUP BY kpi_owner_id;


-- === Plagiarism Module ===

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



-- === Seed Data ===

-- 插入 Mock 审稿人数据
-- 注意：在生产环境这些数据应由 Auth 系统生成
INSERT INTO auth.users (id, email, raw_user_meta_data) VALUES 
(gen_random_uuid(), 'reviewer1@example.com', '{"domains": ["AI", "NLP"]}'::jsonb),
(gen_random_uuid(), 'reviewer2@example.com', '{"domains": ["Machine Learning", "Computer Vision"]}'::jsonb),
(gen_random_uuid(), 'reviewer3@example.com', '{"domains": ["Blockchain", "Security"]}'::jsonb)
ON CONFLICT DO NOTHING;

