-- ScholarFlow Database Setup (Dev Mode)
-- 包含清理旧数据、重建无约束表结构以及预置测试数据

-- === 1. 清理旧表 (Drop Tables) ===
DROP VIEW IF EXISTS editor_kpi_stats;
DROP TABLE IF EXISTS plagiarism_reports;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS review_reports;
DROP TABLE IF EXISTS manuscripts;

-- === 2. 重建稿件表 (Manuscripts) ===
CREATE TABLE manuscripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID, -- 新增：关联期刊
    title TEXT NOT NULL,
    abstract TEXT,
    file_path TEXT,
    doi TEXT UNIQUE, -- 新增：DOI
    author_id UUID, 
    editor_id UUID,
    status TEXT DEFAULT 'submitted',
    published_at TIMESTAMPTZ, -- 新增：发布时间
    kpi_owner_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 2a. 新增期刊表 (Journals) ===
CREATE TABLE journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    issn TEXT,
    impact_factor FLOAT4,
    cover_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 为 manuscripts 添加对 journals 的外键关联
ALTER TABLE manuscripts ADD CONSTRAINT fk_manuscript_journal FOREIGN KEY (journal_id) REFERENCES journals(id);

-- === 3. 重建查重报告表 (Plagiarism) ===
CREATE TABLE plagiarism_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE,
    external_id TEXT,
    similarity_score FLOAT4 DEFAULT 0.0,
    report_url TEXT,
    status TEXT DEFAULT 'pending',
    retry_count INT2 DEFAULT 0,
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 4. 重建财务账单表 (Invoices) ===
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE,
    amount NUMERIC(10, 2) NOT NULL,
    pdf_url TEXT,
    status TEXT DEFAULT 'unpaid',
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_manuscript_invoice UNIQUE (manuscript_id)
);

-- === 5. 重建审稿报告表 (Reviews) ===
CREATE TABLE review_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE,
    reviewer_id UUID,
    token TEXT UNIQUE,
    expiry_date TIMESTAMPTZ,
    status TEXT DEFAULT 'invited',
    content TEXT,
    score INTEGER CHECK (score >= 1 AND score <= 5),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 6. 预置测试数据 (Seed Data) ===
INSERT INTO manuscripts (id, title, abstract, status) 
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Deep Learning in Academic Workflows', 'A comprehensive study on using AI agents to automate peer review processes.', 'submitted'),
    ('00000000-0000-0000-0000-000000000002', 'Quantum Encryption in Data Storage', 'Exploring new methods for securing research data using quantum keys.', 'submitted');

-- 为测试稿件 1 生成初始查重记录
INSERT INTO plagiarism_reports (manuscript_id, status, similarity_score)
VALUES ('00000000-0000-0000-0000-000000000001', 'completed', 0.15);

-- 为测试稿件 2 生成待支付账单
INSERT INTO invoices (manuscript_id, amount, status)
VALUES ('00000000-0000-0000-0000-000000000002', 1500.00, 'unpaid');

-- === Seed Journals ===

INSERT INTO journals (id, title, slug, description, impact_factor) 
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Frontiers in Artificial Intelligence', 'ai-ethics', 'Exploring the intersection of AI, ethics, and society.', 8.4),
    ('22222222-2222-2222-2222-222222222222', 'Journal of Precision Medicine', 'medicine', 'Advanced clinical studies and genomic research.', 12.1);

-- 将之前的测试稿件关联到期刊
UPDATE manuscripts SET journal_id = '11111111-1111-1111-1111-111111111111', status = 'published', published_at = NOW(), doi = '10.1234/sf.2026.001' 
WHERE id = '00000000-0000-0000-0000-000000000001';
