# Handoff: ME Workspace / Intake Queue 设计评估与首屏空列表根因分析

## Session Metadata
- Created: 2026-03-12 20:25:03
- Project: /root/scholar-flow
- Branch: main
- Session duration: ~50 分钟

### Recent Commits (for context)
  - 5c0f910 feat: add revision request manual email endpoints
  - 2ce99df feat: add technical revision manual email endpoints
  - f2f6961 fix(ci): resolve backend pytest warning filter and update frontend lockfile
  - ca73484 chore(artifacts): add submission handoff and mock files
  - 8ce0fd5 docs(intake): align copy with workspace waiting-author flow

## Handoff Chain

- **Continues from**: [2026-03-12-164746-submission-source-selector.md](./2026-03-12-164746-submission-source-selector.md)
  - Previous title: Submission Source Selector UX 收口
- **Supersedes**: None

> Review the previous handoff for full context before filling this one.

## Current State Summary

本次工作没有改代码，主要完成了两部分分析：一是判断 ME 的 `Intake Queue` 与 `Managing Workspace` 这套信息架构是不是合理；二是定位“首次进入页面经常空、需要手动点刷新才有数据”的真实原因。当前结论是：后端把这两个页面设计成“动作队列”和“全流程跟踪台”并非毫无逻辑，但前端与文案没有把边界讲清，而且实现层还存在认证恢复竞态、空结果/旧结果缓存、缓存失效不完整、错误被吞掉直接表现成空列表的问题，所以用户现在感受到的重复和不稳定都是真问题。

## Codebase Understanding

## Architecture Overview

ME 相关页面的数据链路分成两层语义：

- `frontend/src/app/(admin)/editor/intake/page.tsx` 是入口动作面，进入页面后在客户端 `useEffect` 中调用 `editorService.getIntakeQueue()` 拉取 `/api/v1/editor/intake`。
- `frontend/src/app/(admin)/editor/managing-workspace/page.tsx` 是全流程跟踪面，进入页面后在客户端 `useEffect` 中调用 `editorService.getManagingWorkspace()` 拉取 `/api/v1/editor/managing-workspace`。
- `frontend/src/services/editor-api/manuscripts.ts` 为这两个接口都加了前端 GET 缓存和 inflight 去重；`frontend/src/components/editor/ManagingWorkspacePanel.tsx` 与 `frontend/src/app/(admin)/editor/intake/page.tsx` 组件内部又各自有一层 20 秒缓存。
- `backend/app/api/v1/editor_precheck.py` 为 `/workspace` 与 `/managing-workspace` 又加了 8 秒后端短缓存，并要求必须通过鉴权与角色检查。
- 真正的业务边界定义在后端 service：
  - `backend/app/services/editor_service_precheck_intake.py` 明确把 Intake 定义为 `status=pre_check` 且 `pre_check_status=intake/null` 的“待 ME 首次处理队列”。
  - `backend/app/services/editor_service_precheck_workspace_views.py` 把 Managing Workspace 定义为覆盖 pre-check / awaiting_author / under_review / revision / decision / production 的“非终态全流程聚合工作台”。

从架构上说，这不是两个重复接口，而是一个“动作视图”和一个“控制塔视图”。问题在于：workspace 仍包含 `intake` bucket，导致同一批稿件会在两个页面同时出现，前端文案又没有把这个边界解释清楚。

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `frontend/src/components/editor/ManagingWorkspacePanel.tsx` | ME Workspace 前端主体 | 首屏客户端拉数、组件级缓存、错误吞掉后显示空列表的关键位置 |
| `frontend/src/app/(admin)/editor/intake/page.tsx` | Intake Queue 前端主体 | 与 workspace 同类问题在此也存在，且文案直接暴露了“过渡期”状态 |
| `frontend/src/services/editor-api/manuscripts.ts` | Editor 相关 GET/POST API 封装 | 前端 15 秒缓存、inflight 去重、`force refresh` 头部，以及 cache invalidation 缺口都在这里 |
| `frontend/src/services/auth.ts` | 基于 Supabase session 的 token 获取 | 首屏列表请求与 session 恢复并行，形成潜在鉴权竞态 |
| `frontend/src/components/layout/SiteHeader.tsx` | Header 登录态恢复 | 也会在页面进入时单独调用 `getSession()`，说明认证恢复与列表请求没有统一前置控制 |
| `backend/app/api/v1/editor_precheck.py` | ME/AE pre-check 路由与后端短缓存 | `/intake`、`/workspace`、`/managing-workspace` 的角色要求与 8 秒缓存定义在这里 |
| `backend/app/services/editor_service_precheck_intake.py` | Intake 业务定义 | 证明 Intake 是“待首次处理队列”，不是“ME 所有稿件” |
| `backend/app/services/editor_service_precheck_workspace_views.py` | Managing Workspace 分桶逻辑 | 证明 Workspace 是全流程聚合台，但也保留了 `intake` bucket，造成概念重叠 |
| `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md` | 最近的收口设计文档 | 文档明确写了 Phase 1 / Phase 2，说明现在是“过渡期实现”，并非终态设计 |

## Key Patterns Discovered

- 该项目常用“双层甚至三层短 TTL 缓存”来保护 editor 页面性能：组件内缓存 + `EditorApi` 缓存 + 后端短缓存。
- Editor 页面大量采用“客户端 mount 后再请求”的模式，而不是在 App Router page Server Component 中先拿首屏数据。
- 这类页面在失败时经常只 `console.error`，然后关闭 loading，不给错误态 UI；因此用户感知通常会退化成“空列表”。
- 文案与设计文档会直接记录“过渡期兼容”逻辑，说明不少页面不是最终信息架构，而是中间态落地。

## Work Completed

### Tasks Finished

- [x] 审阅前端 ME `Intake Queue` / `Managing Workspace` 页面实现
- [x] 审阅后端 `/api/v1/editor/intake` 与 `/api/v1/editor/managing-workspace` 的职责与状态分桶
- [x] 用 Context7 查询 Next.js App Router 首屏数据获取的官方推荐方向
- [x] 用 Context7 查询 Supabase session 恢复 / `getSession()` / `onAuthStateChange` 相关口径
- [x] 给出产品层结论：当前拆分不是完全错误，但存在严重认知重叠
- [x] 给出实现层结论：首屏空列表并非“没数据”，而是竞态 + 缓存 + 错误处理共同导致

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `.claude/handoffs/2026-03-12-202503-me-workspace-intake-design-review.md` | 新增本次 session handoff 文档 | 供后续会话无歧义接续分析或开始修复 |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| 将当前问题拆成“产品设计是否合理”与“首屏为什么会空”两条线分析 | 只谈 UX；只谈代码；分层分析 | 用户当前抱怨同时包含信息架构混乱与实现不稳定，两者不能混为一谈 |
| 判断“拆成两个工作面”本身可以成立，但当前不是好设计 | 合并成一个页面；保留两个完全独立页面；保留两个视图但收敛边界 | 后端职责语义是说得通的，但 `workspace` 保留 `intake` bucket 导致和独立 `intake` 页面概念重叠 |
| 先不改代码，只输出高置信度根因 | 直接修；先分析再修 | 用户本轮核心问题是“这是一个好的设计吗，为什么这样设计”，先把判断和根因讲清更重要 |

## Pending Work

## Immediate Next Steps

1. 给用户产出一版“收口后的 ME 信息架构方案”，明确推荐是：
   - 方案 A：保留两个页面，但 `Managing Workspace` 不再展示 `intake` bucket；
   - 方案 B：保留一个主页面，把 `Intake Queue` 降级为默认 tab / 快捷过滤视图。
2. 给出“最小修复方案”并开始改代码，优先处理首屏空列表：
   - 增加显式错误态，而不是失败后显示空列表；
   - 避免在认证恢复未完成前就发 protected fetch；
   - 在关键 mutation 后补齐 `managingWorkspaceCache` 失效。
3. 如用户确认要修，实现后至少补定向测试：
   - ME workspace / intake 在请求失败时应显示错误，不是空态；
   - `assignAE` / `submitIntakeRevision` 后 managing workspace 缓存应被失效；
   - 若采用认证门控，补首屏加载行为测试。

## Blockers/Open Questions

- [ ] 是否允许本轮直接改信息架构：这是产品层变更，不只是 bugfix，最好让用户明确选择“继续两个页面”还是“收口成一个主页面”。
- [ ] 如果只做最小修复，是否接受保留当前双页面结构，仅先修空列表和缓存失效问题。
- [ ] 当前项目是否已有统一的“认证已恢复后再拉 protected data”的 hook / gate；本次没有继续全仓追这个公共抽象。

## Deferred Items

- 不直接重构为 Server Component 首屏取数：虽然这是更稳妥的 Next.js 方向，但变更面较大，本次先停在分析阶段。
- 不立即检查所有 editor 页面是否有相同竞态：本次聚焦 ME `intake` 与 `managing-workspace`。
- 不处理 UX 命名收口（例如把 `technical_followup` 改成“等 AE”）：这属于信息架构优化，需要用户确认方向。

## Context for Resuming Agent

## Important Context

最重要的结论有四条：

1. 不要把当前问题简化成“前端没刷新”。真实问题不是一个按钮问题，而是：
   - 首屏请求过早；
   - 失败后错误态缺失；
   - 多层缓存可能缓存空结果或旧结果；
   - mutation 后 managing workspace 缓存没有完整失效。

2. 不要把 `Intake Queue` 和 `Managing Workspace` 当成两个简单重复页面。后端本意是：
   - `Intake` = ME 首次动作队列；
   - `Managing Workspace` = ME 全流程跟踪台。
   但当前因为 `Managing Workspace` 还保留 `intake` bucket，所以用户认知上会觉得重复，这个抱怨是合理的。

3. 设计文档本身已经证明现在是过渡期，不是收口终态：
   - `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md` 第 350 行附近明确写了 Phase 1 / Phase 2。
   - Phase 2 的方向就是把等待作者的稿件移出 Intake，统一放到 Managing Workspace 的 `awaiting_author` 分组。

4. 如果下个会话要直接修 bug，优先级建议是：
   - P0：不要再让请求失败伪装成空列表；
   - P0：补 managing workspace cache invalidation；
   - P1：加认证恢复门控或统一 session-ready 机制；
   - P2：再做信息架构收口。

## Assumptions Made

- 假设用户本轮主要想得到产品判断与原因解释，而不是立刻提交代码修改。
- 假设“手动刷新后数据出现”多数时候不是数据库瞬时变化，而是前端 `force refresh` 绕过缓存/竞态后的表现。
- 假设 Next.js 16 App Router 页面在这里仍然更适合用服务端首屏数据获取模式；该判断已用 Context7 官方文档做了基本校验。
- 假设当前 worktree 基本干净；本次运行 `git status --short` 未见本地改动输出。

## Potential Gotchas

- `create_handoff.py` 这类脚本不在项目根目录，而在 skill 目录 `/root/.codex/skills/session-handoff/scripts/`。不要再从 repo `scripts/` 下找。
- `ManagingWorkspacePanel` 与 `MEIntakePage` 都有各自组件级 20 秒缓存，单看 `EditorApi` 容易漏掉这一层。
- `EditorApi` 的 `invalidateManagingWorkspaceCache()` 已经存在，但业务 mutation 基本没有调用它；修复时优先复用现有 API，不要重复造缓存清理函数。
- `SiteHeader` 也会并行恢复 session，这说明“页面 mount 即请求”与“认证恢复”没有一个统一的 gating 点；修复时可能需要找公共抽象，而不是只在单页里打补丁。
- 后端 `/api/v1/editor/managing-workspace` 也有 8 秒短缓存，前端改完后如果只手测一次，很容易被后端缓存误导。

## Environment State

### Tools/Services Used

- `exec_command`: 用于阅读代码、查找引用、生成 handoff、查看本地状态
- `Context7`: 查询 Next.js 16.1.6 与 Supabase JS v2.58.0 官方文档
- `spawn_agent`: 并行做前端加载根因与后端职责边界分析
- 本次未运行测试、未启动开发服务器、未改业务代码

### Active Processes

- 无已知长期运行进程由本次会话启动
- 未启动 `bun dev`、`uvicorn`、`start.sh`

### Environment Variables

- `NEXT_PUBLIC_API_URL`
- `BACKEND_ORIGIN`
- `SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Related Resources

- `frontend/src/components/editor/ManagingWorkspacePanel.tsx`
- `frontend/src/app/(admin)/editor/intake/page.tsx`
- `frontend/src/services/editor-api/manuscripts.ts`
- `frontend/src/services/auth.ts`
- `frontend/src/components/layout/SiteHeader.tsx`
- `backend/app/api/v1/editor_precheck.py`
- `backend/app/services/editor_service_precheck_intake.py`
- `backend/app/services/editor_service_precheck_workspace_views.py`
- `docs/plans/2026-03-12-precheck-ae-assignment-decoupling-design.md`
- `docs/plans/2026-03-11-current-workflow-for-uat.md`
- Next.js App Router data fetching docs (queried via Context7)
- Supabase JS auth session docs (queried via Context7)

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
