# Quickstart: Editor Performance Refactor

## 1. 前置条件

- 已在分支 `001-editor-performance-refactor`。
- 本地可运行前后端（`./start.sh`）。
- 有可用编辑账号（至少覆盖 managing_editor、assistant_editor、editor_in_chief、admin）。
- 有一批固定样本稿件（建议包含“时间线多、任务多、审稿记录多”的高负载稿件）。

## 2. 本地/预发布启动

```bash
./start.sh
```

如仅跑测试可使用：

```bash
./scripts/test-fast.sh
```

## 3. 基线采样（改前/改后都执行一次）

### 3.1 编辑详情页

1. 打开同一篇高负载稿件详情页。
2. 记录：
- 首屏可操作时间（可点击核心动作）
- 首屏请求数量
- 时间线与卡片加载完成时间
3. 在相同网络条件下重复 10 次，输出 p50/p95。

可用脚本快速落盘（每个场景各执行一次）：

```bash
scripts/perf/capture-editor-baseline.sh \
  --output specs/001-editor-performance-refactor/artifacts/baseline-before.json \
  --scenario editor_detail \
  --p50 3100 \
  --p95 4800 \
  --requests 18
```

如需自动采样 API TTFB（自动计算 p50/p95）：

```bash
scripts/perf/capture-editor-baseline.sh \
  --output specs/001-editor-performance-refactor/artifacts/baseline-before-detail-api.json \
  --scenario editor_detail \
  --requests 1 \
  --auto-url "https://<your-backend>/api/v1/editor/manuscripts/<manuscript-id>?skip_cards=true" \
  --token "<bearer-token>" \
  --samples 12
```

### 3.2 Process / Workspace

1. 打开 `/editor/process`，执行一次关键筛选与搜索。
2. 打开 `/editor/workspace`，执行一次刷新与一次关键动作（如提交检查后刷新）。
3. 记录首屏可操作时间与请求数，重复 10 次。

### 3.3 审稿候选搜索

1. 进入详情页并打开审稿分配弹窗。
2. 用同一关键词做“首次搜索 + 20 秒内重复搜索”对比。
3. 记录首次与重复查询耗时比例。

### 3.4 一键采样 detail/process/workspace（API TTFB）

```bash
scripts/perf/capture-editor-api-baselines.sh \
  --base-url "https://<your-backend>" \
  --token "<bearer-token>" \
  --manuscript-id "<manuscript-id>" \
  --samples 12 \
  --prefix baseline-before-api
```

## 4. 功能回归（分层）

### Tier 1（开发中）

```bash
./scripts/test-fast.sh
```

### Tier 2（提交前）

```bash
cd backend && pytest tests/unit/test_reviewer_service.py tests/integration/test_editor_timeline.py
cd ../frontend && bun run test -- --run
```

### Tier 3（合并前）

```bash
./scripts/run-all-tests.sh
```

## 5. 发布门禁验证（预发布/线上）

### 5.1 Feature 性能门禁（基线对比 + 报告）

```bash
scripts/validate-editor-performance.sh
```

脚本会自动生成：
- `specs/001-editor-performance-refactor/artifacts/baseline-compare.json`
- `specs/001-editor-performance-refactor/artifacts/regression-report.md`

### 5.2 Release Validation（readiness/regression/finalize）

使用 release validation 脚本执行 GO/NO-GO：

```bash
BASE_URL="https://<your-backend>" \
ADMIN_API_KEY="<admin-key>" \
FEATURE_KEY="001-editor-performance-refactor" \
ENVIRONMENT="staging" \
scripts/validate-production-rollout.sh
```

建议同时保存：
- readiness/regression 输出摘要
- report JSON
- 本次基线与历史基线对比表

## 6. 验收通过标准（对应 spec）

- 详情页 p95 首屏可操作 <= 3s，且较基线提升 >= 30%。
- process/workspace p95 首屏可操作 <= 2.5s。
- 审稿候选重复查询耗时 <= 首次查询的 50%。
- 任一链路劣化 >10% 或全量回归失败则判定 NO-GO。
