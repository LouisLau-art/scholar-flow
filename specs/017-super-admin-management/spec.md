# Feature Specification: 超级用户管理后台 (Super Admin User Management)

**Feature Branch**: `017-super-admin-management`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "开启 Feature 017: 超级用户管理后台 (Super Admin User Management)。目前系统仅支持用户自助注册为 Author，缺乏对 Editor 和 Reviewer 角色的管理入口。本功能旨在为"超级管理员 (Super Admin)"提供一个用户权限管理界面。"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - 查看和管理用户列表 (Priority: P1)

超级管理员需要查看系统中的所有注册用户，以便了解用户构成并进行管理。管理员应该能够通过邮箱、姓名、角色等条件筛选和搜索用户。

**Why this priority**: 这是管理员执行所有其他管理操作的基础。没有用户列表，管理员无法看到哪些用户需要管理，也无法进行角色变更或其他操作。

**Independent Test**: 管理员登录后，可以在管理后台看到"用户管理"菜单，点击后显示所有注册用户的列表，并可以使用搜索框和筛选器查找特定用户。

**Acceptance Scenarios**:

1. **Given** 管理员已登录到管理后台，**When** 管理员点击"用户管理"菜单，**Then** 系统显示注册用户列表的第一页（20-30条记录），包含邮箱、姓名、角色和注册时间等信息，并提供分页导航
2. **Given** 管理员在用户管理页面，**When** 管理员在搜索框中输入邮箱地址，**Then** 系统显示匹配该邮箱前缀的用户（支持模糊匹配）
3. **Given** 管理员在用户管理页面，**When** 管理员选择"Editor"角色筛选器，**Then** 系统只显示角色为Editor的用户，并应用服务器端分页

---

### User Story 2 - 修改用户角色 (Priority: P2)

超级管理员需要能够修改用户的角色，特别是将普通作者(Author)晋升为编辑(Editor)或审稿人(Reviewer)，以满足系统运营需求。

**Why this priority**: 角色管理是用户管理的核心功能，直接关系到系统的权限分配和运营效率。

**Independent Test**: 管理员在用户详情页可以修改用户角色，系统会验证管理员权限并记录角色变更操作。

**Acceptance Scenarios**:

1. **Given** 管理员在用户列表页面，**When** 管理员点击某个用户的"详情"按钮，**Then** 系统显示用户详情页，包含角色修改下拉菜单和变更原因输入框
2. **Given** 管理员在用户详情页填写了变更原因，**When** 管理员将角色从"Author"改为"Editor"并确认，**Then** 系统验证管理员权限，更新用户角色，记录变更原因，并显示成功消息
3. **Given** 管理员在用户详情页未填写变更原因，**When** 管理员尝试修改用户角色，**Then** 系统显示验证错误，要求输入变更原因
4. **Given** 管理员在用户详情页，**When** 管理员尝试将超级管理员角色修改为其他角色，**Then** 系统显示错误提示，禁止此操作

---

### User Story 3 - 直接创建内部编辑账号 (Priority: P3)

超级管理员需要能够直接创建内部编辑账号，无需对方注册，系统自动发送账户开通通知和初始登录凭证。

**Why this priority**: 这简化了内部团队成员的加入流程，提高了运营效率，特别是对于需要快速扩充编辑团队的情况。

**Independent Test**: 管理员可以输入邮箱和姓名创建新的Editor账号，系统会自动发送账户通知邮件。

**Acceptance Scenarios**:

1. **Given** 管理员在用户管理页面，**When** 管理员点击"新增内部成员"按钮，**Then** 系统显示创建表单，要求输入邮箱和姓名
2. **Given** 管理员填写了有效的邮箱和姓名，**When** 管理员提交表单，**Then** 系统创建已验证的Editor账号，并自动触发账户开通通知邮件
3. **Given** 管理员尝试使用已存在的邮箱创建账号，**When** 管理员提交表单，**Then** 系统显示错误提示，告知邮箱已存在

---

### User Story 4 - 审稿人临时账号创建 (Priority: P3)

编辑在指派审稿任务时，如果输入的邮箱在系统中不存在，系统应该能够创建临时的审稿人账号并发送审稿邀请链接。

**Why this priority**: 这简化了审稿人邀请流程，编辑无需事先让审稿人注册账号，可以直接邀请外部专家参与审稿。

**Independent Test**: 编辑在指派审稿人时输入新邮箱，系统提示创建临时账号，确认后系统创建Reviewer账号并发送邀请链接。

**Acceptance Scenarios**:

1. **Given** 编辑在稿件审稿人指派页面，**When** 编辑输入一个系统中不存在的邮箱地址，**Then** 系统提示"用户不存在，是否创建临时审稿账号？"
2. **Given** 编辑确认创建临时审稿账号，**When** 编辑点击确认按钮，**Then** 系统自动创建Reviewer角色账号，并发送包含Magic Link的审稿邀请邮件
3. **Given** 编辑取消创建临时账号，**When** 编辑点击取消按钮，**Then** 系统返回审稿人指派页面，不创建任何账号

### Edge Cases

- 当管理员尝试修改自己的角色时，系统应该禁止此操作并显示错误提示，防止意外失去管理权限
- 当系统尝试发送邮件但邮件服务失败时，用户创建操作应该失败回滚，账号不创建，并向管理员显示邮件发送失败的错误信息
- 当编辑尝试创建临时审稿人账号，但输入的邮箱格式无效时，系统应该显示验证错误，要求输入有效的邮箱地址
- 当管理员搜索用户时，如果搜索结果为空，应该显示"未找到匹配用户"的友好提示信息
- 当多个管理员同时修改同一个用户的角色时，系统应该使用乐观锁或类似机制处理并发冲突，确保数据一致性
- 当创建内部编辑账号时，如果姓名字段包含特殊字符或过长，系统应该进行适当的清理和截断，或显示验证错误
- 当审稿人通过Magic Link登录后，系统仅允许通过Magic Link登录，无需设置密码，这是临时账号的安全策略

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: 系统必须在管理员后台提供"用户管理"菜单入口
- **FR-002**: 系统必须展示注册用户列表，使用服务器端分页（每页20-30条记录），包含邮箱、姓名、角色和注册时间等基本信息
- **FR-003**: 系统必须支持按邮箱、姓名和角色进行用户搜索和筛选，邮箱和姓名搜索支持前缀模糊匹配
- **FR-004**: 系统必须在用户详情页提供角色修改功能，允许将Author角色变更为Editor或Reviewer
- **FR-005**: 系统必须验证角色修改操作的执行者具有超级管理员权限
- **FR-006**: 系统必须提供"新增内部成员"功能，允许管理员直接创建Editor角色账号
- **FR-007**: 系统必须在创建内部编辑账号时自动发送账户开通通知邮件
- **FR-008**: 系统必须在编辑指派审稿人时，为不存在的邮箱提供临时审稿账号创建功能
- **FR-009**: 系统必须在创建临时审稿账号时发送包含Magic Link的审稿邀请邮件
- **FR-010**: 系统必须记录所有用户管理操作（角色变更、账号创建等）的审计日志
- **FR-011**: 系统必须验证创建账号时邮箱地址的唯一性，防止重复创建
- **FR-012**: 系统必须提供适当的错误提示，当用户管理操作失败时给出清晰的原因说明
- **FR-013**: 角色变更操作必须要求管理员输入变更原因，作为审计日志的一部分

### Security & Authentication Requirements *(mandatory)*

<!--
  ACTION REQUIRED: Based on Constitution Principle XIII (Security & Authentication)
  All sensitive operations MUST require authentication. Never allow unauthenticated access to user-specific data.
-->

- **SEC-001**: 所有用户管理操作必须要求超级管理员身份验证（Principle XIII）
- **SEC-002**: API端点必须在每次请求时验证JWT令牌（Principle XIII）
- **SEC-003**: 使用认证上下文中的真实用户ID，绝不使用硬编码或模拟ID（Principle XIII）
- **SEC-004**: 为不同用户类型实施适当的基于角色的访问控制（RBAC）（Principle XIII）
- **SEC-005**: 必须在初始设计中解决安全考虑（Principle XIII）
- **SEC-006**: 角色修改操作必须在后端进行二次鉴权，确保操作者拥有超级管理员权限
- **SEC-007**: 用户列表访问必须限制为超级管理员，防止普通用户查看其他用户信息
- **SEC-008**: 账号创建操作必须使用安全的服务角色密钥，防止权限提升攻击
- **SEC-009**: 所有管理操作必须记录审计日志，包含操作者、时间、操作类型和受影响用户

### API Development Requirements *(mandatory)*

<!--
  ACTION REQUIRED: Based on Constitution Principle XIV (API Development Standards)
  API-first design: Define API contracts (OpenAPI/Swagger) BEFORE implementation.
-->

- **API-001**: 必须在实现之前定义API规范（OpenAPI/Swagger）（Principle XIV）
- **API-002**: 使用一致的路径模式（除非必要，否则不使用尾部斜杠）（Principle XIV）
- **API-003**: 始终对API进行版本控制（例如，`/api/v1/`）（Principle XIV）
- **API-004**: 每个端点必须有清晰的文档（Principle XIV）
- **API-005**: 使用中间件实现统一的错误处理（Principle XIV）
- **API-006**: 为所有关键操作提供详细的日志记录（Principle XIV）
- **API-007**: 用户管理API必须遵循RESTful设计原则，使用适当的HTTP方法
- **API-008**: 批量操作必须支持适当的限制和分页，防止性能问题
- **API-009**: API响应必须包含适当的状态码和错误消息，便于前端处理

### Test Coverage Requirements *(mandatory)*

<!--
  ACTION REQUIRED: Based on Constitution Principle XII (Testing Strategy & Coverage)
  Complete API testing: Test ALL HTTP methods (GET, POST, PUT, DELETE) for every endpoint.
-->

- **TEST-001**: 为每个端点测试所有HTTP方法（GET、POST、PUT、DELETE）（Principle XII）
- **TEST-002**: 确保前端和后端API路径完全匹配（Principle XII）
- **TEST-003**: 每个需要认证的端点必须有有效/缺失/无效认证的测试（Principle XII）
- **TEST-004**: 测试所有输入验证规则（必填字段、长度限制、格式约束）（Principle XII）
- **TEST-005**: 测试错误情况，不仅仅是正常路径（Principle XII）
- **TEST-006**: 包含使用真实数据库连接的集成测试（Principle XII）
- **TEST-007**: 在交付前达到100%测试通过率（Principle XI）
- **TEST-008**: 测试超级管理员权限验证逻辑，确保非管理员无法访问用户管理功能
- **TEST-009**: 测试角色修改操作的边界情况，包括尝试修改自己的角色
- **TEST-010**: 测试账号创建操作的并发处理，防止重复创建
- **TEST-011**: 测试邮件发送失败时的错误处理逻辑
- **TEST-012**: 测试用户搜索和筛选功能的性能和准确性

### Key Entities *(include if feature involves data)*

- **用户 (User)**: 系统中的注册用户，包含基本身份信息和角色权限。关键属性包括：用户ID、邮箱、姓名、角色（Author/Editor/Reviewer/Admin）、注册时间、最后登录时间等。
- **角色变更记录 (RoleChangeLog)**: 记录用户角色变更的历史，用于审计和追踪。关键属性包括：变更ID、用户ID、原角色、新角色、变更时间、操作者ID、变更原因（必填字段，用于记录变更理由）等。
- **账号创建记录 (AccountCreationLog)**: 记录通过管理后台创建的账号信息，特别是内部编辑和临时审稿账号。关键属性包括：创建ID、用户ID、创建类型（内部编辑/临时审稿）、创建时间、操作者ID、邀请状态等。
- **邮件通知记录 (EmailNotificationLog)**: 记录系统发送的邮件通知，用于追踪邮件发送状态。关键属性包括：邮件ID、收件人邮箱、邮件类型（账户开通/审稿邀请）、发送时间、发送状态、失败原因等。

## Clarifications

### Session 2026-01-31

- Q: 用户列表的分页策略是什么？如何处理大量用户？ → A: 使用服务器端分页，每次加载20-30条记录
- Q: 用户搜索功能是否支持模糊匹配？还是必须精确匹配？ → A: 支持邮箱和姓名的前缀模糊匹配
- Q: 角色变更操作是否需要记录变更原因？ → A: 需要记录变更原因，作为审计日志的一部分

## Assumptions

- 系统已经实现了基本的用户认证和授权机制
- 超级管理员角色已经存在并具有适当的权限
- Feature 011的邮件系统已经就绪并可以集成使用
- Supabase Admin API可用且配置了适当的服务角色密钥
- 用户数据模型已经包含必要的字段（邮箱、姓名、角色等）
- 前端管理后台的基本框架已经存在，可以添加新的菜单项

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 超级管理员能够在30秒内找到并查看任何注册用户的详细信息
- **SC-002**: 管理员能够在1分钟内完成用户角色变更操作，包括验证和确认步骤
- **SC-003**: 内部编辑账号创建流程在2分钟内完成，包含邮件发送确认
- **SC-004**: 临时审稿账号创建成功率超过95%，邀请邮件在5分钟内送达
- **SC-005**: 用户搜索功能在1000条用户记录中能在1秒内返回搜索结果
- **SC-006**: 所有用户管理操作都有完整的审计日志，可追溯率达到100%
- **SC-007**: 管理员对用户管理界面的满意度评分超过4.5分（5分制）
- **SC-008**: 角色权限错误发生率降低到0.1%以下
