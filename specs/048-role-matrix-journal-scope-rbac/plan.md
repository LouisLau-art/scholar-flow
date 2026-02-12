# Implementation Plan: GAP-P1-05 Role Matrix + Journal-scope RBAC

**Branch**: `048-role-matrix-journal-scope-rbac` | **Date**: 2026-02-09 | **Spec**: `/root/scholar-flow/specs/048-role-matrix-journal-scope-rbac/spec.md`  
**Input**: Feature specification from `/root/scholar-flow/specs/048-role-matrix-journal-scope-rbac/spec.md`

## Summary

本特性的目标是把“角色可用但边界偏粗”的现状收敛为“角色矩阵可解释 + 期刊作用域可执行 + 高风险操作可审计”的生产级治理能力。

核心交付分三层：

1. **角色矩阵层**：统一定义角色能力（页面/按钮/动作/状态流转），替换分散在路由与组件里的隐式规则。  
2. **期刊作用域层**：新增 user-journal scope 绑定，并在关键接口执行角色 + scope 双校验。  
3. **决策与审计层**：显式区分 first/final decision；对 APC/Owner/final decision 强化最小权限与审计。

## Technical Context

**Language/Version**: Python 3.14+（local）/ 3.12（HF Docker）, TypeScript 5.x (strict)  
**Primary Dependencies**: FastAPI 0.115+, Pydantic v2, Supabase-py v2, Next.js 14.2, React 18  
**Storage**: Supabase PostgreSQL（`user_profiles`, `journals`, `manuscripts`, `invoices`, `status_transition_logs`）  
**Testing**: pytest（contract/integration/unit）, Vitest, Playwright（mocked E2E）  
**Project Type**: full-stack web (backend + frontend + migration)  
**Constraints**:
- 保持现有身份体系（Supabase JWT + `user_profiles.roles`），不引入外部 IAM。
- Admin 保持平台级能力，其余角色默认受 journal scope 约束。
- 兼容 legacy `editor` 角色，避免一次性切换导致回归。

## Constitution Check

### Pre-Design Gate

- **I. 胶水编程**: PASS  
  复用现有 `user_profiles`、`journals`、`status_transition_logs`，新增最小关系表与权限服务。
- **II. 测试优先**: PASS  
  每个用户故事先落 RBAC/scope 回归测试，再落实现。
- **III. 安全优先**: PASS  
  高风险操作采用后端硬校验；前端仅作 UX 辅助，不作为安全边界。
- **IV. 持续同步**: PASS  
  Feature 规格化后同步 GAP 文档和三份上下文文件（AGENTS/CLAUDE/GEMINI）。
- **V. 环境一致**: PASS  
  继续使用云端 Supabase + `bun`/`uv`。

## Project Structure

### Documentation (this feature)

```text
/root/scholar-flow/specs/048-role-matrix-journal-scope-rbac/
├── spec.md
├── plan.md
└── tasks.md
```

### Planned Source Touchpoints

```text
/root/scholar-flow/supabase/migrations/
└── 20260210110000_create_journal_role_scopes.sql

/root/scholar-flow/backend/
├── app/core/role_matrix.py                    # 新增：角色矩阵与动作权限
├── app/core/journal_scope.py                  # 新增：期刊作用域校验
├── app/services/decision_service.py           # final decision 权限与语义收敛
├── app/services/editor_service.py             # process 列表 scope 裁剪
├── app/api/v1/editor.py                       # 关键接口加 scope + 最小权限
├── app/api/v1/admin/users.py                  # （可选）scope 管理接口
└── tests/
    ├── contract/test_api_paths.py
    ├── integration/test_rbac_journal_scope.py
    └── unit/test_role_matrix_scope.py

/root/scholar-flow/frontend/
├── src/types/user.ts
├── src/services/editorApi.ts
├── src/app/(admin)/editor/process/page.tsx
├── src/app/(admin)/editor/manuscript/[id]/page.tsx
├── src/app/(admin)/editor/decision/[id]/page.tsx
├── src/components/DecisionPanel.tsx
└── tests/
    ├── unit/rbac-visibility.test.tsx
    └── e2e/specs/rbac-journal-scope.spec.ts
```

## Rollout Strategy

1. **Phase A（兼容发布）**: 默认开启 role matrix；journal scope 先在读接口灰度告警（可配置）。  
2. **Phase B（强校验）**: 对关键写接口（owner/APC/final decision）启用强制 scope 403。  
3. **Phase C（全量收敛）**: Process/Detail/Decision 全链路按 scope 裁剪并补齐 E2E。

## Risks & Mitigations

- **风险 1**: 旧 `editor` 账号无 scope 绑定导致批量 403。  
  **缓解**: 提供兼容映射 + 启动期审计日志 + 一键补数脚本。

- **风险 2**: 关键路径权限收紧导致线上操作中断。  
  **缓解**: 分阶段开关发布，先读后写，写接口先从最小集合开始。

- **风险 3**: 前后端权限文案不一致造成误解。  
  **缓解**: 统一权限错误码与提示文案；前端按钮显示基于后端返回的 capability。

## Complexity Tracking

当前无宪法豁免项。
