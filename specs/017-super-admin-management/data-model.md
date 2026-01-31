# 数据模型设计: 超级用户管理后台

**Feature**: 017-super-admin-management
**Date**: 2026-01-31
**Purpose**: 定义本功能涉及的数据实体、关系和验证规则

## 核心实体

### 1. 用户 (User)
系统中已存在的用户实体，本功能需要扩展使用。

**现有属性**:
- `id`: UUID - 用户唯一标识
- `email`: string - 用户邮箱（唯一）
- `name`: string - 用户姓名
- `role`: enum('author', 'editor', 'reviewer', 'admin') - 用户角色
- `created_at`: timestamp - 注册时间
- `last_sign_in_at`: timestamp - 最后登录时间

**本功能新增要求**:
- 角色字段需要支持本功能的角色变更操作
- 需要记录用户创建来源（普通注册/管理员创建/临时审稿）

### 2. 角色变更记录 (RoleChangeLog)
记录用户角色变更的审计日志。

**属性**:
- `id`: UUID - 记录唯一标识
- `user_id`: UUID (外键 → users.id) - 被操作用户
- `operator_id`: UUID (外键 → users.id) - 操作者（超级管理员）
- `old_role`: enum('author', 'editor', 'reviewer', 'admin') - 原角色
- `new_role`: enum('author', 'editor', 'reviewer', 'admin') - 新角色
- `reason`: text - 变更原因（必填，长度限制：10-500字符）
- `ip_address`: string - 操作者IP地址
- `user_agent`: string - 操作者浏览器信息
- `created_at`: timestamp - 操作时间（默认当前时间）

**验证规则**:
- `reason`字段必填，长度10-500字符
- `operator_id`必须是超级管理员角色
- 禁止`old_role` == `new_role`的变更
- 禁止超级管理员修改自己的角色

### 3. 账号创建记录 (AccountCreationLog)
记录通过管理后台创建的账号信息。

**属性**:
- `id`: UUID - 记录唯一标识
- `user_id`: UUID (外键 → users.id) - 创建的用户
- `creator_id`: UUID (外键 → users.id) - 创建者（超级管理员）
- `creation_type`: enum('internal_editor', 'temporary_reviewer') - 创建类型
- `invitation_status`: enum('pending', 'sent', 'delivered', 'opened', 'failed') - 邀请状态
- `invitation_sent_at`: timestamp - 邀请发送时间
- `invitation_opened_at`: timestamp - 邀请打开时间
- `created_at`: timestamp - 创建时间（默认当前时间）

**验证规则**:
- `internal_editor`类型账号必须已验证邮箱
- `temporary_reviewer`类型账号使用Magic Link登录
- 邀请邮件发送失败需要记录失败原因

### 4. 邮件通知记录 (EmailNotificationLog)
记录系统发送的邮件通知状态。

**属性**:
- `id`: UUID - 记录唯一标识
- `recipient_email`: string - 收件人邮箱
- `template_type`: enum('editor_account_created', 'reviewer_invitation') - 邮件模板类型
- `user_id`: UUID (外键 → users.id, 可为空) - 关联用户（如已存在）
- `status`: enum('queued', 'sent', 'delivered', 'opened', 'failed') - 发送状态
- `failure_reason`: text - 失败原因（仅当status='failed'时）
- `sent_at`: timestamp - 发送时间
- `delivered_at`: timestamp - 送达时间
- `opened_at`: timestamp - 打开时间
- `created_at`: timestamp - 创建时间（默认当前时间）

**验证规则**:
- 邮箱地址格式验证
- `failure_reason`仅当`status='failed'`时必填

## 关系图

```
用户 (User)
  ├── 1:n ── 角色变更记录 (RoleChangeLog) [作为被操作用户]
  ├── 1:n ── 角色变更记录 (RoleChangeLog) [作为操作者]
  ├── 1:1 ── 账号创建记录 (AccountCreationLog) [作为创建的用户]
  └── 1:1 ── 账号创建记录 (AccountCreationLog) [作为创建者]

账号创建记录 (AccountCreationLog)
  └── 1:1 ── 邮件通知记录 (EmailNotificationLog)

邮件通知记录 (EmailNotificationLog)
  └── 0:1 ── 用户 (User) [如果用户已存在]
```

## 状态转换

### 用户角色状态转换
```
作者 (author) → 编辑 (editor) ✓
作者 (author) → 审稿人 (reviewer) ✓
编辑 (editor) → 审稿人 (reviewer) ✓
审稿人 (reviewer) → 编辑 (editor) ✓
超级管理员 (admin) → 任何其他角色 ✗ (禁止)
任何角色 → 超级管理员 (admin) ✗ (禁止 - 需特殊流程)
```

### 账号创建状态转换
```
待创建 → 已创建 → 邀请发送中 → 邀请已发送 → 邀请已送达 → 邀请已打开
       ↓          ↓
       创建失败    邀请发送失败
```

## 数据库迁移脚本

```sql
-- 创建角色变更记录表
CREATE TABLE role_change_logs (
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

-- 创建账号创建记录表
CREATE TABLE account_creation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creation_type VARCHAR(20) NOT NULL CHECK (creation_type IN ('internal_editor', 'temporary_reviewer')),
    invitation_status VARCHAR(20) DEFAULT 'pending' CHECK (invitation_status IN ('pending', 'sent', 'delivered', 'opened', 'failed')),
    invitation_sent_at TIMESTAMP WITH TIME ZONE,
    invitation_opened_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_creation UNIQUE (user_id, creation_type)
);

-- 创建邮件通知记录表
CREATE TABLE email_notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_email VARCHAR(255) NOT NULL,
    template_type VARCHAR(30) NOT NULL CHECK (template_type IN ('editor_account_created', 'reviewer_invitation')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'failed')),
    failure_reason TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT email_format CHECK (recipient_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT failure_reason_required CHECK (
        (status != 'failed' OR failure_reason IS NOT NULL) AND
        (status = 'failed' OR failure_reason IS NULL)
    )
);

-- 创建索引优化查询性能
CREATE INDEX idx_role_change_user ON role_change_logs(user_id);
CREATE INDEX idx_role_change_operator ON role_change_logs(operator_id);
CREATE INDEX idx_role_change_created ON role_change_logs(created_at DESC);

CREATE INDEX idx_account_creation_user ON account_creation_logs(user_id);
CREATE INDEX idx_account_creation_creator ON account_creation_logs(creator_id);

CREATE INDEX idx_email_notification_email ON email_notification_logs(recipient_email);
CREATE INDEX idx_email_notification_user ON email_notification_logs(user_id);
CREATE INDEX idx_email_notification_status ON email_notification_logs(status);
```

## 验证规则总结

1. **用户角色变更**:
   - 禁止超级管理员修改自己的角色
   - 变更原因必填，长度10-500字符
   - 新旧角色不能相同

2. **账号创建**:
   - 内部编辑账号必须邮箱已验证
   - 临时审稿账号使用Magic Link
   - 邮箱地址唯一性验证

3. **邮件通知**:
   - 邮箱格式验证
   - 失败原因记录

这个数据模型设计支持本功能的所有业务需求，同时确保数据完整性和审计追踪能力。