# Handoff: Submission Source Selector UX 收口

## Session Metadata
- Created: 2026-03-12 16:47:46
- Project: /root/scholar-flow
- Branch: main
- Session duration: 约 1 小时

### Recent Commits (for context)
  - 7bf6b10 feat(submission): add manuscript source selector
  - c0460eb fix(submission): allow source archive metadata
  - 419e8ea fix(review): trim timeline and relax exit guard
  - 4e24e3d test(reviews): align invite integration mocks
  - 123466c fix(submission): tolerate stale schema cache

## Handoff Chain

- **Continues from**: None (fresh start)
- **Supersedes**: None

> This is the first handoff for this task.

## Current State Summary

本轮工作聚焦作者投稿页的 `Word manuscript` / `LaTeX ZIP` 互斥交互收口。此前虽然前后端都已有 `Word XOR ZIP` 约束，但作者侧 UI 仍同时暴露两个上传入口，用户可以误以为两者都能提交。当前已经完成正式改造并推送到 `origin/main`：投稿页现在先要求选择 `Manuscript Source (Choose One)`，再只显示单一上传卡片；切换 source type 时会弹确认并清空当前 source 文件；后端仍保留 XOR 校验兜底。当前没有未提交代码改动，只有两个本地未跟踪 mock 文件残留。最后推送提交是 `7bf6b10 feat(submission): add manuscript source selector`。

## Codebase Understanding

## Architecture Overview

作者投稿链路的核心分三层：

1. 前端 `SubmissionForm` 负责页面编排与渲染顺序；
2. `use-submission-form` 负责状态机、文件上传、解析、门禁、最终提交 payload；
3. 后端 `/api/v1/manuscripts` 负责 Pydantic 校验、`manuscript_word_path XOR source_archive_path` 约束和 `manuscript_files` 落库。

这一轮只改前端交互表达，不改后端 API 契约。也就是说：

- UI 通过 source type selector 明确表达互斥关系；
- hook 通过 `selectedSourceType` 和 reset key 管理单一路径状态；
- 后端继续作为最后防线拒绝非法 `Word + ZIP` 双传请求。

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `frontend/src/components/SubmissionForm.tsx` | 投稿页主编排组件 | 现在负责在 Cover Letter 后插入 source type selector，并按选择条件渲染单一 source upload card |
| `frontend/src/components/submission/use-submission-form.ts` | 投稿表单主 hook | 本轮最重要文件；新增 `selectedSourceType`、切换确认逻辑、source-specific finalize 门禁和 file input reset |
| `frontend/src/components/submission/SubmissionSourceTypeSelector.tsx` | 新增 source type 选择器 | 作者先在这里选 `word` 或 `zip`，未选前不显示任何 source 上传卡片 |
| `frontend/src/components/submission/SubmissionSourceTypeSwitchDialog.tsx` | 新增切换确认弹窗 | 已上传一种 source 后切到另一种时，必须先确认再清空当前 source 文件 |
| `frontend/src/components/submission/SubmissionWordUploadCard.tsx` | Word 上传卡片 | 去掉旧的“被另一条路径禁用”的表达，改成在被选中时才出现 |
| `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx` | ZIP 上传卡片 | 同上，只在 ZIP route 被选中时显示 |
| `frontend/src/tests/SubmissionForm.test.tsx` | 投稿页前端行为测试 | 本轮先红后绿的主测试文件，已覆盖 selector、switch dialog、finalize gating 和 ZIP 路径 |
| `backend/tests/test_manuscripts.py` | 后端投稿契约最小验证 | 用于确认 `Word XOR ZIP + cover letter` 契约在 UI 调整后仍保持成立 |
| `docs/plans/2026-03-12-submission-source-type-selector-design.md` | 本轮 UX 设计说明 | 记录为何放弃“双卡片禁用”，改为“先选 source type 再显示单一卡片” |
| `docs/plans/2026-03-12-submission-source-type-selector-implementation-plan.md` | 本轮执行计划 | checklist 已全部勾完，适合作为恢复上下文的第一入口 |

## Key Patterns Discovered

- 投稿表单相关状态统一放在 `use-submission-form`，页面组件尽量只做编排，不重复持有业务状态。
- 文件输入的重置不依赖直接操作 DOM，而是使用 React 官方推荐的 `key` 重建模式；本轮通过 `wordInputResetKey` / `sourceArchiveInputResetKey` 实现。
- 高风险交互仍保持最小 TDD：先改 `SubmissionForm.test.tsx` 让测试红，再补实现，再跑最小后端契约验证。
- 后端契约尽量不为 UI 让步；作者侧 UI 可以更清楚，但 `manuscript_word_path XOR source_archive_path` 不能下放成“仅前端约束”。

## Work Completed

## Tasks Finished

- [x] 为作者投稿页新增 `Manuscript Source (Choose One)` 选择器
- [x] 改成未选择 source type 前不显示 Word/ZIP 上传卡片
- [x] 增加 source type 切换确认弹窗，并在确认后清空当前 source 文件
- [x] 删除旧的双卡片禁用表达，改成真正的“单一路径显示”
- [x] 更新 finalize 门禁，使其依赖 `selectedSourceType + 对应 source 文件 + PDF + cover letter`
- [x] 同步更新 UAT/workflow/open-items 文档
- [x] 运行最小前端和后端验证并通过

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `frontend/src/components/SubmissionForm.tsx` | 插入 selector 和 switch dialog，按 source type 条件渲染上传卡片 | 从页面层直接表达 `Word` / `ZIP` 互斥关系 |
| `frontend/src/components/submission/use-submission-form.ts` | 新增 `selectedSourceType`、`pendingSourceType`、dialog 状态和切换确认逻辑；收紧 finalize 校验 | 把互斥关系和切换逻辑集中到单一 hook 中维护 |
| `frontend/src/components/submission/SubmissionSourceTypeSelector.tsx` | 新增组件 | 让作者先做路线选择，而不是被两个上传框误导 |
| `frontend/src/components/submission/SubmissionSourceTypeSwitchDialog.tsx` | 新增组件 | 避免 source type 切换时隐式删除当前文件 |
| `frontend/src/components/submission/SubmissionWordUploadCard.tsx` | 去掉 `disabled` 语义和“另一路已选”提示 | 选中后才显示，不再需要双卡片互相提示 |
| `frontend/src/components/submission/SubmissionSourceArchiveUploadCard.tsx` | 同上 | 保持 Word/ZIP 两条路径对称 |
| `frontend/src/tests/SubmissionForm.test.tsx` | 调整并新增 selector/switch/finalize 行为测试 | 先红后绿，锁住 UX 变更 |
| `docs/plans/2026-03-11-current-workflow-for-uat.md` | 更新作者投稿页面顺序和 source type 规则 | 避免 UAT 按旧流程验收 |
| `docs/plans/2026-03-10-open-work-items.md` | 更新“投稿文件入口已收成 source selector” | 让开放待办与代码现状一致 |
| `docs/plans/2026-03-12-submission-source-type-selector-*.md` | 新增设计文档和 implementation plan | 为后续 agent 恢复上下文提供成体系说明 |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| 用“先选 source type，再显示单一上传入口”替代“双卡片同时显示 + 禁用另一边” | 双卡片禁用、后端报错拦截、单一入口 selector | selector 能从源头消除歧义，用户心智最清楚 |
| 切换 source type 时弹确认，而不是直接替换已上传文件 | 直接清空、软提示、确认弹窗 | 切换本质上是 destructive action，应该显式确认 |
| 保留后端 `Word XOR ZIP` 强校验，不因 UI 改好而删除后端兜底 | 仅前端限制、前后端双重限制 | 投稿链路属于高风险业务边界，前后端都要守住 |
| file input reset 继续用 `key` 驱动重建 | 手动改 DOM value、key reset | React 官方文档更推荐 key reset，状态更稳定 |

## Pending Work

## Immediate Next Steps

1. 在真实 UAT 环境再手工验证一轮作者投稿：分别走 `Word route` 和 `ZIP route`，确认页面行为与线上提交都正常。
2. 查看 `7bf6b10` 之后的 GitHub Actions / Vercel / HF 部署结果；这次 push 仍是直接推 `main`，远端提示 required checks 被绕过等待。
3. 如果用户继续推进投稿链路，优先评估是否需要把同样的 source type UX 带到作者 revision 页面；当前这轮只改了首次投稿。

## Blockers/Open Questions

- [ ] Open question: 作者 revision 页面是否也需要采用同样的 `source type selector` 模型。目前只明确了首次投稿。
- [ ] Open question: 是否需要在编辑侧详情页进一步突出 `source_archive` 与 `word manuscript` 的区别展示；当前主链已可用，但展示层还有优化空间。

## Deferred Items

- `frontend` 全量 `tsc` / 全仓回归未在这轮扩大执行，因为 AGENTS.md 明确要求“验证最小”，且本任务聚焦投稿表单交互。
- 投稿链路之外的 decision / reviewer / academic 主线未在本轮继续推进，因为用户这轮明确把优先级转到了作者投稿 UX。

## Context for Resuming Agent

## Important Context

最重要的是：这轮已经明确放弃“Word 和 ZIP 两个上传框同时显示，然后靠禁用/报错拦住”的做法。用户先要求从 UI/UX 角度想清楚，再动手改，所以设计已经定死成：

- 先选 `Manuscript Source (Choose One)`
- 再只显示对应的单一上传卡片
- 如果已经上传了一种 source，再切换到另一种，必须先弹确认
- `PDF manuscript` 和 `Cover letter` 仍然是独立必传项
- 后端继续保留 `Word XOR ZIP` 约束，绝不能因为 UI 变好了就放松

本轮已经完成实现并 push 到 `origin/main`，提交是 `7bf6b10 feat(submission): add manuscript source selector`。如果下一位 agent 接手，不要再往“双卡片禁用”那条路回退。

另外，当前工作区只有两个未跟踪文件：

- `mock_cover_letter.pdf`
- `mock_latex_submission.zip`

它们是本地调试残留，不要误提交。

## Assumptions Made

- 假设当前用户需求只覆盖“首次投稿页”，不自动扩展到 revision 页。
- 假设 ZIP 路线继续维持“仅存储、不解析元数据”的产品口径。
- 假设后端 `Word XOR ZIP + cover letter` 契约已经是正确产品规则，因此本轮只改前端交互表达。

## Potential Gotchas

- `SubmissionForm.test.tsx` 仍会打出一些 React `act(...)` warning；这不是本轮新引入的问题，当前测试结果本身是通过的。
- push 到 `main` 时远端仍提示 `3 of 3 required status checks are expected`，说明代码已推上去，但 required checks 没有先等完。
- 若后续继续动投稿链路，记得不要把本地 mock 文件一起 `git add`。
- `use-submission-form.ts` 是投稿页的中心状态文件，任何“顺手改一点”都很容易把 finalize gating 或上传路径打歪，继续改这里时要先跑定向测试。

## Environment State

## Tools/Services Used

- `brainstorming` skill：先收需求和 UX 方向，再决定不使用“双卡片禁用”
- `ux-researcher-designer` skill：确定 selector-first 是更好的交互表达
- `writing-plans` / `executing-plans` skills：先写设计文档与 implementation plan，再按 checklist 实施
- `test-driven-development` skill：先修改 `SubmissionForm.test.tsx` 让核心行为变红，再补实现
- `shadcn-ui` skill：参考现有 `RadioGroup` / `Dialog` 组件模式落 selector 和 confirm dialog
- `Context7`：查询 React 官方关于 `key` 重置组件状态的最新文档口径
- `Vitest`：前端投稿页最小行为验证
- `pytest`：后端投稿契约最小验证

## Active Processes

- 无需保留的后台进程。本次测试命令均已结束。

## Environment Variables

- `NEXT_PUBLIC_API_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY`
- `GEMINI_METADATA_MODEL`

## Related Resources

- `docs/plans/2026-03-12-submission-source-type-selector-design.md`
- `docs/plans/2026-03-12-submission-source-type-selector-implementation-plan.md`
- `docs/plans/2026-03-11-current-workflow-for-uat.md`
- `docs/plans/2026-03-10-open-work-items.md`
- `frontend/src/components/SubmissionForm.tsx`
- `frontend/src/components/submission/use-submission-form.ts`
- `frontend/src/tests/SubmissionForm.test.tsx`
- React docs lookup via Context7: resetting component state with `key` when switching input contexts

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
