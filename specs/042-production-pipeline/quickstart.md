# Quickstart: Production Pipeline Workspace (Feature 042)

## 1. 环境准备

1. 在云端 Supabase 应用本 Feature 迁移（新增 `production_cycles`、`production_proofreading_responses`、`production_correction_items` 及 `production-proofs` bucket）。
2. 准备一篇状态为 `approved` 的稿件，且具备可登录作者与编辑用户。
3. 确保站内通知机制可用（用于“待校对/待修订/可发布”提醒）。
4. 若启用 `PRODUCTION_GATE_ENABLED=1`，确认核准环节会同步发布门禁所需文件字段。

## 2. 编辑端流程验收

### Scenario A: 创建轮次并发送清样

1. 进入编辑页面 `/editor/production/{manuscript_id}`。
2. 创建生产轮次，选择排版负责人和校对责任作者，设置截止时间。
3. 上传 PDF 清样并填写版本说明。
4. 预期结果：
   - 轮次状态变为 `awaiting_author`。
   - 作者收到“清样待校对”通知。
   - 审计日志记录 `production_cycle_created` 与 `galley_uploaded` 事件。

### Scenario B: 作者提交修正清单后回到排版

1. 作者打开 `/proofreading/{manuscript_id}` 查看清样。
2. 提交 `submit_corrections`，至少填写 1 条 correction item。
3. 编辑端刷新工作间，接收“待排版修订”提醒并进入修订处理。
4. 预期结果：
   - 轮次状态经历 `author_corrections_submitted -> in_layout_revision`。
   - 作者不能对同一轮次重复提交反馈。

### Scenario C: 作者确认无误并核准发布依据

1. 排版上传修订后清样，轮次回到 `awaiting_author`。
2. 作者提交 `confirm_clean`。
3. 编辑执行“Approve for Publication”。
4. 预期结果：
   - 轮次状态为 `approved_for_publish`。
   - 发布动作只能引用该核准轮次对应版本。

## 3. 权限与异常验收

1. 非归属编辑访问编辑工作间应返回 403。
2. 非责任作者提交校对反馈应返回 403。
3. 同稿件存在活跃轮次时，再次创建轮次应返回 409。
4. 截止后提交校对反馈应返回 422 并带逾期提示。

## 4. 测试建议命令

```bash
# 后端（快速验证，不触发全局覆盖率门槛）
cd /root/scholar-flow/backend
pytest -o addopts= tests/unit/test_production_workspace_service.py
pytest -o addopts= tests/integration/test_production_workspace_api.py
pytest -o addopts= tests/integration/test_proofreading_author_flow.py

# 前端单测
cd /root/scholar-flow/frontend
bun run test:run \
  tests/unit/production-workspace.test.tsx \
  tests/unit/author-proofreading.test.tsx \
  tests/unit/production-approval.test.tsx \
  tests/unit/production-timeline.test.tsx

# E2E（先跑 chromium）
bun run test:e2e tests/e2e/specs/production_pipeline.spec.ts --project=chromium
```

## 5. 完成判定

满足以下条件即可进入 `/speckit.tasks`：
- 三条核心业务路径（清样上传、作者校对、发布核准）均可独立通过验收。
- 权限与边界场景（403/409/422）可稳定复现。
- 审计日志可完整回放生产轮次关键事件。

## 6. 本轮实现验收记录（2026-02-09）

```bash
cd /root/scholar-flow/backend
pytest -o addopts= tests/unit/test_production_workspace_service.py
# => 6 passed

pytest -o addopts= tests/integration/test_production_workspace_api.py \
  tests/integration/test_proofreading_author_flow.py \
  tests/integration/test_production_publish_gate.py \
  tests/integration/test_production_workspace_audit.py
# => 7 skipped（依赖云端迁移/数据条件，符合预期）

cd /root/scholar-flow/frontend
bun run test:run \
  tests/unit/production-workspace.test.tsx \
  tests/unit/author-proofreading.test.tsx \
  tests/unit/production-approval.test.tsx \
  tests/unit/production-timeline.test.tsx
# => 4 files passed, 7 tests passed

bun run test:e2e tests/e2e/specs/production_pipeline.spec.ts --project=chromium
# => 2 passed
```
