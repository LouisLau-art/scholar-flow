# Decision / Academic Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 ScholarFlow 的 pre-check、academic decision、first/final decision、reviewer 复审选择与邮件通知语义收口为一套可审计、可统计 AE 绩效、符合真实编辑部分工的工作流。

**Architecture:** 把现有混杂的流程拆成三条独立轴线：`稿件状态`、`人员绑定/改派`、`外部学术意见`。内部编辑部负责执行真实状态变更与作者邮件；外部角色（reviewer / academic editor / editor_in_chief）负责输出学术意见或 recommendation。前后端继续沿用 `Next.js 16.1.6 App Router + FastAPI 0.115.x + Supabase` 现有结构，小步重构，先锁测试再改实现。

**Tech Stack:** Next.js 16.1.6 App Router, React 19, TypeScript 5.x, FastAPI 0.115.x, Pydantic v2, Supabase/PostgreSQL, Vitest, pytest

---

## Context / Constraints

- 当前真实流程说明：`docs/plans/2026-03-11-current-workflow-for-uat.md`
- 当前开放待办：`docs/plans/2026-03-10-open-work-items.md`
- 用户已明确的新业务口径：
  - `academic_editor` 与 `editor_in_chief` 同属编委会，在 academic/decision 链路上权限等价
  - reviewer / academic editor / EIC 都属于外部编委，只给建议，不直接代表编辑部执行内部动作
  - 编辑部（ME / AE / admin 等内部角色）负责真正状态变更、邮件模板选择与作者通知
  - pre-check 技术退回必须有单独状态，且不能污染 AE 绩效
  - 多轮 reviewer 发送对象必须由编辑部显式决定，不能由系统根据上一轮按钮自动推断
  - 站内通知不是主链路，关键通知以邮件为准

## Non-goals

- 本轮不做 reviewer / academic editor 的完整登录体系重构
- 本轮不把所有历史 decision 数据一次性迁移成新枚举，先保兼容层
- 本轮不扩展 production / finance 无关链路

## Execution Checklist

- [x] Phase 1: 低风险语义收口
- [x] Phase 2: 学术结论 5 选项模型落地（兼容底座）
- [x] Phase 3: `revision_before_review` + AE SLA 起点
- [x] Phase 4: recommendation-only 与编辑部执行分层
- [ ] Phase 5: reviewer 多轮显式选择
- [ ] Phase 6: 邮件模板与 smoke/UAT 文档收尾（进行中）

## Phase Breakdown

### Phase 1

目标：先修正当前最误导用户、但改动风险最低的语义问题，为后续大改铺底。

- 把所有用户可见的 `Add Reviewer` 收口为 `Add Additional Reviewer`
- 收掉 `editor_in_chief` 在 academic/decision 链路上的特殊 bypass
- 让 `academic_editor` / `editor_in_chief` 在 academic queue / final decision queue 上都按稿件绑定过滤
- 保持内部枚举 `add_reviewer` 不变，避免立刻迁移历史数据

### Phase 2

目标：把学术编辑决策收成你定义的 5 个明确结论，避免编辑部靠长 comments 猜学术含义。

- 新 recommendation 枚举：
  - `accept`
  - `accept_after_minor_revision`
  - `major_revision`
  - `reject_resubmit`
  - `reject_decline`
- first decision / final decision 共用同一组 recommendation，是否允许执行由所处阶段决定
- reviewer 保持现有 report 模型，但 academic editor / EIC 的 recommendation 单独建模

### Phase 3

目标：引入 pre-check 技术退回独立状态，隔离 AE 绩效统计。

当前进度：
- 已完成 `revision_before_review` 状态与作者修回回流 `pre_check/intake|technical`
- 已完成 `initial_submitted_at / latest_author_resubmitted_at / ae_sla_started_at` 持久化与最小 backfill
- 后续若要真正做绩效报表，仍需单独补 analytics / API 聚合口径

- 新状态：`revision_before_review`
- 保留首次投稿时间，不重写 `submitted_at`
- 新增或收口以下统计字段：
  - `initial_submitted_at`
  - `latest_author_resubmitted_at`
  - `ae_sla_started_at`
- 作者从 `revision_before_review` 修回后，重新进入 AE workspace，并重置 `ae_sla_started_at`

### Phase 4

目标：把“学术意见”和“编辑部执行”彻底拆开。

当前进度：
- 已完成 academic pre-check recommendation-only：academic editor / EIC 提交 recommendation 时不再直接推进到 `under_review / decision`
- 已完成 recommendation 审计落盘与详情/queue 可见：记录 `precheck_academic_recommendation_submitted`，并在 academic queue / manuscript detail 展示 recommendation 与 note
- 已完成编辑部执行入口：Managing Editor / Admin 现在可在 `pre_check/academic` 手动推进到 `under_review / decision`
- 已完成 decision workspace recommendation-only：academic editor / EIC 在 `decision / decision_done` 里提交 recommendation 时，不再直接触发 manuscript status 变化或作者通知，而是写入 `decision_recommendation_submitted` 审计；内部编辑继续保留 execute 模式
- 当前 `Decision Workspace` 已按 `submission_mode = recommendation | execute` 分层，前端也已改为 recommendation-only 文案与 5 个标准学术结论
- 作者信模板映射仍在后续 Phase 6 处理中

- academic editor / EIC 只提交 recommendation，不直接修改稿件主状态
- AE / ME / admin 执行真正的状态变更
- 作者决策信模板改由编辑部根据 recommendation 选择
- 作者邮件以 email 为主，不把站内通知当关键闭环

### Phase 5

目标：把多轮 reviewer 选择从“系统暗推”改成“编辑部显式控制”。

当前进度：
- 已完成第一刀：作者在 `major_revision` 修回后，系统不再自动复用上一轮 completed reviewer 创建新一轮 `review_assignments`
- 当前 major/minor revision 修回统一回到 `resubmitted`，是否再次进入 `under_review`、以及发给哪些 reviewer，改由编辑部后续手动决定
- 已完成第二刀：`review-stage-exit.target_stage = first` 的 `requested_outcome` 已从旧的 workflow bucket 收口为 5 个 academic recommendation 值，Decision Workspace / manuscript detail 的展示文案已同步到 recommendation 语义
- 尚未完成 reviewer selection UI/文案的进一步收口；当前 reviewer assignment modal 仍是手动勾选式，但还缺更明确的“继续哪些 reviewer / 新增哪些 reviewer”分层表达

- `add additional reviewer` 只表达建议扩充 reviewer 池
- 下一轮具体发给谁，由编辑部显式勾选：
  - 延续哪些已有 reviewer
  - 停掉哪些 reviewer
  - 新增哪些 reviewer
- 系统不再根据上一轮 `major/minor` 自动决定二轮 reviewer

### Phase 6

目标：收尾邮件、UAT、回归验证与文档。

当前进度：
- 已完成 author decision notification 的 email-first 底座：`_notify_author()` 现在会根据 decision / latest academic recommendation 生成 `template_key` 并发送 inline email，站内通知保留为补充
- 已完成 recommendation -> author template key 的最小映射底座，包括：
  - `decision_accept`
  - `decision_accept_after_minor_revision`
  - `decision_major_revision`
  - `decision_minor_revision`
  - `decision_reject`
  - `decision_reject_resubmit`
  - `decision_reject_decline`
- 已完成最小 route 级 smoke：
  - `pre_check/academic recommendation -> editorial execute(decision)` 会写入 `precheck_academic_recommendation_submitted` 与 `precheck_academic_to_decision`
  - `pre_check/academic recommendation -> editorial execute(under_review)` 会写入 `precheck_academic_recommendation_submitted` 与 `precheck_academic_to_review`
  - `review-stage-exit -> first decision` 会发出 first decision request email，并携带新的 academic recommendation label
  - `final decision execute(reject)` 会优先复用最近一条 `reject_resubmit` recommendation，对作者邮件使用 `decision_reject_resubmit`
- 已完成最小前端 mocked Playwright smoke：
  - `decision_workspace.spec.ts` 覆盖 internal execute mode 与 academic recommendation-only mode
  - `decision_workspace.visual.spec.ts` 已同步到当前 `Decision Workspace` 标题文案
- 已完成一个可选真实环境 deployed smoke 入口：
  - `deployed_smoke.spec.ts` 新增 `SMOKE_DECISION_MANUSCRIPT_ID`
  - 配置真实 admin 账号与 decision 稿件后，可验证 `/editor/decision/[id]` 真实页面可达
- 尚未完成 admin email template 管理、真实模板内容运营化，以及更高层 rollout script 集成

- 邮件模板映射 recommendation -> author template
- reviewer / academic / decision 关键流程补 smoke
- 同步 `docs/plans/2026-03-10-open-work-items.md`
- 更新当前真实流程文档，明确哪些已实现、哪些仍在计划中

---

## Task 1: Phase 1 Low-risk Semantic Alignment

**Files:**
- Create: `frontend/src/lib/decision-labels.ts`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/first_decision_request_email.py`
- Modify: `frontend/src/components/editor/decision/DecisionEditor.tsx`
- Modify: `frontend/src/app/(admin)/editor/decision/[id]/page.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `backend/tests/unit/test_precheck_role_service.py`
- Test: `backend/tests/unit/test_editor_service.py`
- Test: `frontend/src/components/editor/decision/DecisionEditor.test.ts`

**Step 1: Write the failing tests**

```python
def test_ensure_editor_access_rejects_unassigned_editor_in_chief() -> None:
    svc = DecisionService()
    with pytest.raises(HTTPException):
        svc._ensure_editor_access(
            manuscript={"academic_editor_id": "academic-1"},
            user_id="chief-2",
            roles={"editor_in_chief"},
        )
```

```python
def test_submit_academic_check_rejects_unbound_editor_in_chief():
    with pytest.raises(HTTPException):
        svc.submit_academic_check(manuscript_id, "review", changed_by=caller, actor_roles=["editor_in_chief"])
```

```typescript
it('uses add additional reviewer label for add_reviewer option', () => {
  expect(getDecisionOptionLabel('add_reviewer')).toBe('Add Additional Reviewer')
})
```

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py tests/unit/test_precheck_role_service.py tests/unit/test_editor_service.py -q --no-cov
cd frontend && bun run vitest run src/components/editor/decision/DecisionEditor.test.ts
```

Expected:

- backend 失败点命中 `editor_in_chief` 特殊 bypass
- frontend 失败点命中 label 仍为 `Add Reviewer`

**Step 3: Write minimal implementation**

- `DecisionService._ensure_editor_access()` 中只保留 `admin` 跨稿件 bypass
- `submit_academic_check()` 中移除 `editor_in_chief` 的未绑定绕过
- `get_academic_queue()` / `get_final_decision_queue()` 对 `academic_editor` 与 `editor_in_chief` 一致地按 `academic_editor_id` 过滤
- 新增统一 label helper，页面、Decision editor、邮件模板全部共用

**Step 4: Run tests to verify they pass**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py tests/unit/test_precheck_role_service.py tests/unit/test_editor_service.py -q --no-cov
cd frontend && bun run vitest run src/components/editor/decision/DecisionEditor.test.ts
```

Expected: PASS

**Step 5: Verify quality gates**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py tests/unit/test_precheck_role_service.py tests/unit/test_editor_service.py --no-cov
cd frontend && bun run vitest run src/components/editor/decision/DecisionEditor.test.ts
cd frontend && bun run lint
cd frontend && bunx tsc --noEmit
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/decision_service.py \
  backend/app/services/editor_service_precheck_workspace_decisions.py \
  backend/app/services/first_decision_request_email.py \
  backend/tests/unit/test_decision_service_access.py \
  backend/tests/unit/test_precheck_role_service.py \
  backend/tests/unit/test_editor_service.py \
  frontend/src/lib/decision-labels.ts \
  frontend/src/components/editor/decision/DecisionEditor.tsx \
  frontend/src/components/editor/decision/DecisionEditor.test.ts \
  frontend/src/app/'(admin)'/editor/decision/'[id]'/page.tsx \
  frontend/src/app/'(admin)'/editor/manuscript/'[id]'/page.tsx
git commit -m "fix: align academic decision semantics"
```

## Task 2: Introduce 5-option Academic Recommendation Model

**Files:**
- Modify: `backend/app/models/decision.py`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/decision_service_transitions.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `frontend/src/types/decision.ts`
- Modify: `frontend/src/services/editor-api/types.ts`
- Modify: `frontend/src/components/editor/decision/DecisionEditor.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `frontend/src/components/editor/decision/DecisionEditor.test.ts`

**Step 1: Write the failing tests**

```python
def test_first_decision_accept_after_minor_revision_is_allowed_as_recommendation():
    request = DecisionSubmitRequest(
        content="Minor polishing required",
        decision="accept_after_minor_revision",
        is_final=True,
        decision_stage="first",
        attachment_paths=[],
        last_updated_at=None,
    )
    assert request.decision == "accept_after_minor_revision"
```

```typescript
it('shows five academic recommendation options in decision stage config', () => {
  expect(getAcademicRecommendationOptions()).toEqual([
    'accept',
    'accept_after_minor_revision',
    'major_revision',
    'reject_resubmit',
    'reject_decline',
  ])
})
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
cd frontend && bun run vitest run src/components/editor/decision/DecisionEditor.test.ts
```

Expected: FAIL, because new recommendation values do not exist yet

**Step 3: Write minimal implementation**

- 先新增 recommendation enum / type，不立刻删旧值
- 增加 recommendation -> author template key 的映射层
- 前端 Decision editor 改成显示新 recommendation 文案，但后端 transition 仍保兼容判断

**Step 4: Run tests to verify they pass**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
cd frontend && bun run vitest run src/components/editor/decision/DecisionEditor.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/decision.py \
  backend/app/services/decision_service.py \
  backend/app/services/decision_service_transitions.py \
  backend/app/services/editor_service_precheck_workspace_decisions.py \
  frontend/src/types/decision.ts \
  frontend/src/services/editor-api/types.ts \
  frontend/src/components/editor/decision/DecisionEditor.tsx \
  frontend/src/app/'(admin)'/editor/manuscript/'[id]'/page.tsx
git commit -m "feat: add academic recommendation model"
```

## Task 3: Add `revision_before_review` State and AE SLA Start Time

**Files:**
- Create: `supabase/migrations/20260312xxxxxx_revision_before_review_and_ae_sla.sql`
- Modify: `backend/app/models/manuscript.py`
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/editor_service.py`
- Modify: `backend/app/api/v1/editor_precheck.py`
- Modify: `frontend/src/types/precheck.ts`
- Modify: `frontend/src/components/editor/AEWorkspacePanel.tsx`
- Test: `backend/tests/unit/test_precheck_role_service.py`
- Test: `backend/tests/integration/test_precheck_flow.py`

**Step 1: Write the failing test**

```python
def test_submit_technical_check_revision_moves_to_revision_before_review_and_sets_ae_sla():
    out = svc.submit_technical_check(...)
    assert out["status"] == "revision_before_review"
    assert out["ae_sla_started_at"] is not None
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py -q --no-cov
```

Expected: FAIL, because current status is still legacy revision path

**Step 3: Write minimal implementation**

- migration 增加新状态兼容约束与时间字段
- technical revision 改为进入 `revision_before_review`
- 作者修回后，重置 `ae_sla_started_at`

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py tests/integration/test_precheck_flow.py --no-cov
```

Expected: PASS

**Step 5: Commit**

```bash
git add supabase/migrations/20260312xxxxxx_revision_before_review_and_ae_sla.sql \
  backend/app/models/manuscript.py \
  backend/app/services/editor_service_precheck_workspace_decisions.py \
  backend/app/services/editor_service.py \
  backend/app/api/v1/editor_precheck.py \
  frontend/src/types/precheck.ts \
  frontend/src/components/editor/AEWorkspacePanel.tsx
git commit -m "feat: add revision before review workflow"
```

## Task 4: Decouple Assignment / Reassignment from State Machine

**Files:**
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/editor_service.py`
- Modify: `backend/app/api/v1/editor.py`
- Modify: `frontend/src/components/editor/BindingAcademicEditorDropdown.tsx`
- Modify: `frontend/src/components/editor/AEWorkspacePanel.tsx`
- Test: `backend/tests/unit/test_precheck_role_service.py`
- Test: `backend/tests/integration/test_rbac_journal_scope.py`

**Step 1: Write the failing tests**

```python
def test_me_can_rebind_assistant_editor_during_under_review():
    updated = svc.reassign_ae(...)
    assert updated["assistant_editor_id"] == "ae-2"
```

```python
def test_me_can_rebind_academic_editor_after_manuscript_enters_decision():
    updated = svc.bind_academic_editor(...)
    assert updated["academic_editor_id"] == "academic-2"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py tests/integration/test_rbac_journal_scope.py --no-cov
```

Expected: FAIL, because current implementation still couples some assignment actions to workflow stage assumptions

**Step 3: Write minimal implementation**

- 把 `assistant_editor_id` / `academic_editor_id` 明确定义为 assignment，不直接等价于 workflow transition
- 允许内部角色在合法 scope 内改派，不强制要求处于某单一阶段

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py tests/integration/test_rbac_journal_scope.py --no-cov
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/editor_service_precheck_workspace_decisions.py \
  backend/app/services/editor_service.py \
  backend/app/api/v1/editor.py \
  frontend/src/components/editor/BindingAcademicEditorDropdown.tsx \
  frontend/src/components/editor/AEWorkspacePanel.tsx
git commit -m "feat: decouple editorial assignment from workflow state"
```

## Task 5: Make Academic Recommendation Recommendation-only

**Files:**
- Modify: `backend/app/services/editor_service_precheck_workspace_decisions.py`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/api/v1/editor_decision.py`
- Modify: `frontend/src/app/(admin)/editor/academic/page.tsx`
- Modify: `frontend/src/components/editor/decision/DecisionEditor.tsx`
- Test: `backend/tests/unit/test_precheck_role_service.py`
- Test: `backend/tests/unit/test_decision_service_access.py`

**Step 1: Write the failing tests**

```python
def test_submit_academic_check_persists_recommendation_but_does_not_transition_manuscript():
    out = svc.submit_academic_check(...)
    assert out["status"] == "pre_check"
    assert out["academic_recommendation"]["decision"] == "major_revision"
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py tests/unit/test_decision_service_access.py -q --no-cov
```

Expected: FAIL, because current academic action still changes manuscript status directly

**Step 3: Write minimal implementation**

- academic check 改为保存 recommendation record
- Decision workspace / manuscript detail 读取 recommendation
- 编辑部操作按钮单独执行真正 transition

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest tests/unit/test_precheck_role_service.py tests/unit/test_decision_service_access.py -q --no-cov
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/editor_service_precheck_workspace_decisions.py \
  backend/app/services/decision_service.py \
  backend/app/api/v1/editor_decision.py \
  frontend/src/app/'(admin)'/editor/academic/page.tsx \
  frontend/src/components/editor/decision/DecisionEditor.tsx
git commit -m "feat: make academic recommendations recommendation only"
```

## Task 6: Explicit Multi-round Reviewer Selection

**Files:**
- Modify: `backend/app/services/reviewer_service.py`
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/api/v1/editor.py`
- Modify: `frontend/src/components/editor/ReviewerManagementCard.tsx`
- Modify: `frontend/src/app/(admin)/editor/manuscript/[id]/detail-sections.tsx`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `frontend/tests/unit/...` (new reviewer selection test file as needed)

**Step 1: Write the failing tests**

```python
def test_add_additional_reviewer_does_not_auto_select_previous_major_reviewer():
    out = svc.prepare_next_round(...)
    assert out["selected_reviewer_ids"] == ["explicit-choice-1"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
```

Expected: FAIL, because current code path still implies automatic reviewer continuation semantics

**Step 3: Write minimal implementation**

- `add_additional_reviewer` 只生成建议语义
- 下一轮 reviewer 选择通过显式 payload 提交
- UI 展示“existing / additional / removed”三类 reviewer 操作

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
cd frontend && bun run test -- ReviewerManagementCard
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/reviewer_service.py \
  backend/app/services/decision_service.py \
  backend/app/api/v1/editor.py \
  frontend/src/components/editor/ReviewerManagementCard.tsx \
  frontend/src/app/'(admin)'/editor/manuscript/'[id]'/detail-sections.tsx
git commit -m "feat: make reviewer reselection explicit"
```

## Task 7: Email-first Author Notification Mapping

**Files:**
- Modify: `backend/app/services/decision_service.py`
- Modify: `backend/app/services/first_decision_request_email.py`
- Modify: `backend/app/core/mail.py`
- Modify: `backend/app/api/v1/editor_decision.py`
- Test: `backend/tests/unit/test_decision_service_access.py`
- Test: `backend/tests/unit/test_email_templates.py` (create if missing)

**Step 1: Write the failing tests**

```python
def test_reject_resubmit_uses_resubmit_template_key():
    payload = build_author_decision_email_payload(decision="reject_resubmit")
    assert payload["template_key"] == "decision_reject_resubmit"
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
```

Expected: FAIL, because template mapping does not exist yet

**Step 3: Write minimal implementation**

- recommendation -> template key 明确映射
- 决策发信默认走 email，站内通知降为非关键补充
- first decision request / final decision author email 语义同步

**Step 4: Run tests to verify it passes**

Run:

```bash
cd backend && pytest tests/unit/test_decision_service_access.py -q --no-cov
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/decision_service.py \
  backend/app/services/first_decision_request_email.py \
  backend/app/core/mail.py \
  backend/app/api/v1/editor_decision.py
git commit -m "feat: map academic decisions to author email templates"
```

## Task 8: Smoke / Docs / UAT Sync

**Files:**
- Modify: `docs/plans/2026-03-10-open-work-items.md`
- Modify: `docs/plans/2026-03-11-current-workflow-for-uat.md`
- Modify: `scripts/validate-production-rollout.sh` (if decision smoke is extended)
- Modify: relevant Playwright / pytest smoke files as needed

**Step 1: Write the failing test / checklist**

- 列出必须覆盖的真实链路：
  - `pre_check -> revision_before_review -> author resubmit -> AE workspace`
  - `technical -> academic -> recommendation -> editorial execution`
  - `under_review -> first decision request with AE recommendation -> decision workspace recommendation -> editorial execution`
  - `decision_done -> final decision`

**Step 2: Run current smoke to identify missing coverage**

Run:

```bash
./scripts/validate-production-rollout.sh
```

Expected: 明确看到 decision / academic 相关未覆盖点

**Step 3: Write minimal implementation**

- 补 smoke / UAT 文档
- 在 `backend/tests/integration/test_decision_workspace.py` 增加最小 route 级 smoke：
  - `test_academic_recommendation_then_editorial_execute_to_decision_writes_precheck_actions`
  - `test_academic_recommendation_then_editorial_execute_to_review_writes_precheck_actions`
  - `test_review_stage_exit_first_decision_sends_request_email_with_academic_recommendation`
  - `test_final_decision_prefers_latest_recommendation_template_for_author_email`
- 明确“当前已实现”和“仍在规划”的边界

**Step 4: Run verification**

Run:

```bash
cd backend && pytest tests/integration/test_decision_workspace.py -q --no-cov -k 'academic_recommendation_then_editorial_execute_to_decision_writes_precheck_actions or academic_recommendation_then_editorial_execute_to_review_writes_precheck_actions or review_stage_exit_first_decision_sends_request_email_with_academic_recommendation or final_decision_prefers_latest_recommendation_template_for_author_email'
cd backend && ruff check app/api/v1/editor.py app/services/decision_service_transitions.py tests/integration/test_decision_workspace.py tests/unit/test_decision_service_access.py
```

Expected:

- 四条 route 级 smoke 通过
- 关键 decision / academic 改动保持静态检查为绿

**Step 5: Commit**

```bash
git add docs/plans/2026-03-10-open-work-items.md \
  docs/plans/2026-03-11-current-workflow-for-uat.md \
  scripts/validate-production-rollout.sh
git commit -m "docs: sync academic decision workflow rollout plan"
```

---

Plan complete and saved to `docs/plans/2026-03-12-decision-academic-workflow-implementation-plan.md`.

本次会话默认采用“同一 session 内按计划执行第一阶段”的方式推进，不额外切新 session。
