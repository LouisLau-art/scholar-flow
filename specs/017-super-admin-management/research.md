# Research Findings: 超级用户管理后台

**Feature**: 017-super-admin-management
**Date**: 2026-01-31
**Purpose**: 解决技术实现中的未知问题，为设计阶段提供决策依据

## 研究问题与发现

### 1. Supabase Admin API 使用方式

**问题**: 如何使用Supabase的`service_role`密钥绕过普通注册限制创建已验证用户？

**研究发现**:
- Supabase提供Admin API用于服务器端用户管理操作
- `service_role`密钥具有最高权限，可以绕过RLS策略
- 使用`supabase.auth.admin.createUser()`方法可以直接创建已验证用户
- 可以设置用户的邮箱验证状态、角色和其他元数据

**决策**: 使用`supabase-py`的Admin API创建用户，设置`email_confirmed_at`为当前时间，在`user_metadata`中存储角色信息

**Rationale**: 这是Supabase推荐的服务器端用户创建方式，可以完全控制用户状态

**替代方案考虑**:
- 使用普通注册流程+手动验证：需要额外步骤，用户体验差
- 使用Magic Link邀请：适用于临时审稿人，但不适用于内部编辑创建

### 2. 用户角色变更的审计日志设计

**问题**: 如何设计角色变更的审计日志表结构？

**研究发现**:
- 审计日志需要记录：谁、何时、做了什么、为什么
- 需要关联用户ID、操作者ID、变更前后状态
- 应该包含IP地址、用户代理等上下文信息
- 日志应不可篡改，只追加不修改

**决策**: 创建`role_change_logs`表，包含以下字段：
- `id`: UUID主键
- `user_id`: 被操作用户ID
- `operator_id`: 操作者ID（超级管理员）
- `old_role`: 原角色
- `new_role`: 新角色
- `reason`: 变更原因（必填）
- `created_at`: 操作时间
- `ip_address`: 操作者IP地址
- `user_agent`: 操作者浏览器信息

**Rationale**: 完整的审计日志符合安全最佳实践，便于追溯和合规

**替代方案考虑**:
- 仅记录到文件日志：不易查询和分析
- 简化字段：缺少上下文信息，不利于问题排查

### 3. 邮件系统集成（Feature 011）

**问题**: 如何集成Feature 011的邮件系统发送账户开通通知和审稿邀请？

**研究发现**:
- Feature 011已实现基于Resend的邮件系统
- 支持模板化邮件发送
- 提供邮件发送状态追踪
- 有邮件队列和重试机制

**决策**: 复用Feature 011的邮件服务，创建两个新模板：
1. `editor-account-created`: 内部编辑账户开通通知
2. `reviewer-invitation`: 临时审稿人邀请（含Magic Link）

**Rationale**: 避免重复造轮子，保持邮件系统一致性

**替代方案考虑**:
- 使用Supabase Edge Functions发送邮件：增加复杂度
- 直接调用Resend API：绕过现有抽象层

### 4. 分页和搜索的最佳实践

**问题**: 如何处理大量用户数据的分页和高效搜索？

**研究发现**:
- 服务器端分页优于客户端分页，性能更好
- 使用游标分页（cursor-based）比偏移分页（offset-based）更适合大数据集
- Supabase查询支持`range()`方法进行分页
- 对于搜索，使用`ilike`进行前缀匹配比全文搜索更简单高效

**决策**:
- 分页：使用Supabase的`range(start, end)`进行服务器端分页，每页20条记录
- 搜索：邮箱和姓名使用`ilike`进行前缀模糊匹配（如`email.ilike('user%@%')`）
- 排序：默认按注册时间倒序，支持按姓名、邮箱排序

**Rationale**: 平衡性能与实现复杂度，满足大多数使用场景

**替代方案考虑**:
- 使用PostgreSQL全文搜索：功能强大但实现复杂
- 使用Elasticsearch：过度设计，维护成本高

### 5. 临时审稿账号的Magic Link实现

**问题**: 如何为临时审稿人创建安全的Magic Link登录方式？

**研究发现**:
- Supabase Auth支持一次性Magic Link
- Magic Link可以设置过期时间（默认24小时）
- 可以自定义重定向URL和邮件模板
- 临时账号不需要设置密码，安全性更高

**决策**: 使用`supabase.auth.signInWithOtp()`发送Magic Link，设置：
- 过期时间：7天（给审稿人足够时间）
- 重定向到审稿任务页面
- 自定义邮件模板说明这是临时审稿账号

**Rationale**: Magic Link无密码，更安全；临时账号适合外部审稿人场景

**替代方案考虑**:
- 发送临时密码：需要密码管理，安全性较低
- 创建完整账号：给外部审稿人带来负担

## 技术决策总结

1. **用户创建**: 使用Supabase Admin API + `service_role`密钥
2. **审计日志**: 创建专门的`role_change_logs`表记录所有变更
3. **邮件集成**: 复用Feature 011邮件系统，创建两个新模板
4. **分页搜索**: 服务器端分页 + `ilike`前缀模糊匹配
5. **临时账号**: Magic Link邀请，无密码，7天有效期

这些决策基于Supabase最佳实践和项目现有架构，平衡了功能需求、安全性和实现复杂度。