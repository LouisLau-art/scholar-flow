-- ScholarFlow Database Setup (Full Version v1.9.0)
-- 包含：稿件、期刊、查重、财务、审稿任务、种子数据

-- === 1. 清理旧结构 ===
DROP TABLE IF EXISTS review_assignments CASCADE;
DROP TABLE IF EXISTS plagiarism_reports CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS review_reports CASCADE;
DROP TABLE IF EXISTS manuscripts CASCADE;
DROP TABLE IF EXISTS journals CASCADE;

-- === 2. 期刊表 (Journals) ===
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

-- === 3. 稿件表 (Manuscripts) ===
CREATE TABLE manuscripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID REFERENCES journals(id),
    title TEXT NOT NULL,
    abstract TEXT,
    file_path TEXT,
    doi TEXT UNIQUE,
    author_id UUID, -- 这里暂时去掉 REFERENCES auth.users 以便 Demo 测试
    editor_id UUID,
    status TEXT DEFAULT 'submitted', -- submitted, plagiarism_checking, quality_checking, under_review, published
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 4. 查重报告表 (Plagiarism) ===
CREATE TABLE plagiarism_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE,
    similarity_score FLOAT4 DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 5. 审稿任务分配表 (Review Assignments) ===
-- 007 特性新增
CREATE TABLE review_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE,
    reviewer_id UUID, -- 对应审稿人的 Auth UID
    status TEXT DEFAULT 'pending', -- pending, completed
    scores JSONB, -- 存储多维度评分 {novelty: 5, rigor: 4, ...}
    comments TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 6. 财务账单表 (Invoices) ===
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE UNIQUE,
    amount NUMERIC(10, 2) DEFAULT 1500.00,
    status TEXT DEFAULT 'unpaid',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 7. 预置种子数据 (Seed Data) ===

-- 7a. 预置期刊
INSERT INTO journals (id, title, slug, description, impact_factor) 
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Frontiers in Artificial Intelligence', 'ai-ethics', 'Exploring AI, ethics, and society.', 8.4),
    ('22222222-2222-2222-2222-222222222222', 'Journal of Precision Medicine', 'medicine', 'Advanced clinical studies.', 12.1);

-- 7b. 预置稿件 (1篇已发布，1篇正在审)
INSERT INTO manuscripts (id, journal_id, title, abstract, status, published_at, doi, author_id) 
VALUES 
    ('00000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'AI Governance Frameworks', 'A study on global AI policies.', 'published', NOW(), '10.1234/sf.2026.001', '99999999-9999-9999-9999-999999999999'),
    ('00000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Gene Editing in Rare Diseases', 'Clinical trials analysis.', 'submitted', NULL, NULL, '99999999-9999-9999-9999-999999999999');

-- 7c. 预置审稿任务 (分配给一个固定测试 ID)
INSERT INTO review_assignments (manuscript_id, reviewer_id, status)
VALUES ('00000000-0000-0000-0000-000000000002', '88888888-8888-8888-8888-888888888888', 'pending');