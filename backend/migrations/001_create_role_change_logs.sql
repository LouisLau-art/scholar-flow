-- Migration: Create role_change_logs table
-- Created: 2026-01-31
-- Feature: 017-super-admin-management

-- 创建角色变更记录表
CREATE TABLE IF NOT EXISTS role_change_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    old_role VARCHAR(20) NOT NULL CHECK (old_role IN ('author', 'editor', 'reviewer', 'admin')),
    new_role VARCHAR(20) NOT NULL CHECK (new_role IN ('author', 'editor', 'reviewer', 'admin')),
    reason TEXT NOT NULL CHECK (length(reason) BETWEEN 10 AND 500),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT role_change_valid CHECK (old_role != new_role),
    CONSTRAINT not_self_change CHECK (user_id != operator_id)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_role_change_user ON role_change_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_role_change_operator ON role_change_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_role_change_created ON role_change_logs(created_at DESC);
