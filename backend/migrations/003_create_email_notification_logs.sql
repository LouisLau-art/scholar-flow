-- Migration: Create email_notification_logs table
-- Created: 2026-01-31
-- Feature: 017-super-admin-management

-- 创建邮件通知记录表
CREATE TABLE IF NOT EXISTS email_notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_email VARCHAR(255) NOT NULL,
    template_type VARCHAR(30) NOT NULL CHECK (template_type IN ('editor_account_created', 'reviewer_invitation')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'failed')),
    failure_reason TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT DEFAULT NOW(),

    CONSTRAINT email_format CHECK (recipient_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT failure_reason_required CHECK (
        (status != 'failed' OR failure_reason IS NOT NULL) AND
        (status = 'failed' OR failure_reason IS NULL)
    )
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_email_notification_email ON email_notification_logs(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_notification_user ON email_notification_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_notification_status ON email_notification_logs(status);
