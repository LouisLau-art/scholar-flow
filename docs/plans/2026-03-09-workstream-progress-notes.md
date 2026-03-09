# Workstream Progress Notes

日期：2026-03-09
当前代码锚点：`8411912`
分支：`main`
状态：工作区干净（记录创建时）

## 已完成主线

### Next 16 稳定化

- 已完成 `Next 16.1.6 + React 19 + eslint-config-next 16` 工具链对齐。
- 已完成 `middleware -> proxy` 迁移。
- 已完成 async request APIs 第一轮收敛。
- 已补齐 `README.md`、`AGENTS.md`、`docs/DEPLOYMENT.md` 的版本口径。
- 已设置回退锚点：`pre-next16-full-align`。

### Reviewer Invitation / Workspace

- reviewer 必须显式 `Accept` 邀请后才能进入 workspace。
- `session` / `workspace` / `submit` 已移除 implicit accept。
- invite 页已支持稿件基础信息与 PDF 预览。
- decline reasons 已接入 invite 页决策面。
- reviewer 首次激活不再走明文密码，已改为 activation / set-password 流程。

### Manuscript Detail / Reviewer Summary

- 稿件详情页左侧主区已新增 `Reviewer Management`。
- 右侧 `Review Summary` 已收敛为轻量摘要卡。
- 多轮 reviewer 的 `submitted_at` 错绑问题已修复。
- reviewer history modal 已补充 `round / due / decline reason / decline note` 等字段。

## 已写计划与说明文档

- `docs/plans/2026-03-06-next16-stabilization-plan.md`
- `docs/plans/2026-03-06-next16-stabilization-notes.md`
- `docs/plans/2026-03-06-reviewer-invitation-workflow-plan.md`
- `docs/plans/2026-03-06-reviewer-invitation-state-machine-notes.md`

## 当前尚未完成的 reviewer 相关工作

### P1

1. reviewer invitation history 进一步对齐参考图
   - 目标字段：`added by`、`added via`、更完整的 timeline
   - 当前阻塞：现有 schema 尚无稳定数据源

2. 邮件投递证据链收敛
   - 需要把 reviewer invitation 从“时间戳近似”升级为真实 `queued / sent / failed`
   - 当前 `email_logs` 还缺 assignment 级关联字段

3. reviewer 全链路 E2E
   - 目标覆盖：`select -> send invitation -> accept/decline -> workspace -> submit`

### P2

4. re-invite / decline 后重新邀请语义进一步收敛
5. manuscript detail 中 reviewer history 展示继续增强

## 本轮突发问题

### Dashboard 角色误判

现象：任何账号登录后点击 `/dashboard`，都会提示：

> 当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。

当前排查结论：

- 根因范围已锁定在前端 dashboard 的角色归一化逻辑。
- `frontend/src/components/dashboard/DashboardPageClient.tsx` 中的 `normalizeRoleTokens(input)` 当前只接受数组；一旦 `/api/v1/user/profile` 返回字符串或其他非数组结构，就会被错误归一化为空数组。
- `/dashboard` 的 SSR 初始数据也会把非数组 `roles` 直接丢弃，并把 `initialRolesLoaded` 标记为成功，导致页面不再补拉 profile，直接稳定误报。
- 已按 TDD 修复：
  - 新增 `frontend/src/components/dashboard/__tests__/DashboardPageClient.test.tsx`
  - 覆盖 SSR + 客户端 profile fetch 两条回归路径
  - dashboard 现已兼容字符串、JSON 风格字符串和异常拼接格式的角色载荷

## 下一步顺序

1. 继续 reviewer invitation history / email evidence 链路
2. 补 reviewer 主链路 E2E
3. 视需要把相同的 roles 归一化防御收敛到其他依赖 `/api/v1/user/profile` 的页面
