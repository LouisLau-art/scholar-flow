# 鲁总反馈落地记录（2026-02-06）

## 反馈来源
- `docs/NewFeedback/feedback.txt`
- 两张标注流程图（`docs/NewFeedback/*.png`）

## 本次已落地调整

### 1) 拒稿路径收敛
- 统一规则：拒稿只能在 `decision/decision_done` 执行。
- 禁止从 `pre_check`、`under_review`、`resubmitted` 直接进入 `rejected`。
- Quick Pre-check 去掉 `reject`，仅保留 `approve` / `revision`。

### 2) 投稿前期角色顺序修正
- 投稿前期改为 **ME 先做技术/行政审查**，通过后再分配 AE 跟进执行。
- AE 定位调整为“跟进执行角色”，而非投稿入口审查发起者。

## 对应文档改动
- `specs/038-precheck-role-workflow/spec.md`：重写为“ME-first intake + AE follow-up + EIC routing”，并加入 reject 门禁要求。
- `docs/upgrade_plan_v2.md`：更新双重 pre-check 描述、角色职责、Sprint 1 实施项。
- `docs/doc_artifacts/flow_lifecycle.mmd`：入口流程改为 ME 先审；学术不通过改为进入 Decision，再拒稿。
- `docs/doc_artifacts/state_manuscript.mmd`：删除 `Pending_Quality_Check -> Rejected`、`Under_Review -> Rejected` 直连。

## 说明
- `docs/doc_artifacts/*.png/*.svg` 为历史导出产物，当前以 `.mmd` 源文件为准；后续如需重新导出，请基于更新后的 `.mmd` 生成。
