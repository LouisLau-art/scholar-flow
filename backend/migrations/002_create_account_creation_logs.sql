-- Migration: Create account_creation_logs table
-- Created: 2026-01-31
-- Feature: 017-super-admin-management

-- 创建账号创建记录表
CREATE TABLE IF NOT EXISTS account_creation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creation_type VARCHAR(20) NOT NULL CHECK (creation_type IN ('internal_editor', 'temporary_reviewer')),
    invitation_status VARCHAR(20) DEFAULT 'pending' CHECK (invitation_status IN ('pending', 'sent', 'delivered', 'opened', 'failed')),
    invitation_sent_at TIMESTAMP WITH TIME ZONE,
    invitation_opened_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT DEFAULT NOW(),

    CONSTRAINT unique_user_creation UNIQUE (user_id, creation_type)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_account_creation_user ON account_creation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_account_creation_creator ON account_creation_logs(creator_id);
