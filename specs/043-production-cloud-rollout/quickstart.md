# Quickstart: Cloud Rollout Regression (GAP-P0-02)

## 1. 前置条件

1. 当前分支已包含 Feature 042 代码，并已部署到目标后端环境。
2. 云端 Supabase 可访问，且具有 migration 执行权限。
3. 已配置 `ADMIN_API_KEY`，用于调用内部验收接口。
4. 准备一篇可用于回归的测试稿件（已进入 post-acceptance 链路）。

## 2. 云端迁移与环境准备

```bash
cd /root/scholar-flow

# 1) 确认已链接目标项目
supabase projects list

# 2) 检查将要应用的迁移
supabase db push --linked --dry-run

# 3) 应用迁移
supabase db push --linked
```

验收要点：
- `production_cycles` / `production_proofreading_responses` / `production_correction_items` 可查询。
- `release_validation_runs` / `release_validation_checks` 可查询。
- `production-proofs` bucket 可用。

## 3. 一键脚本（推荐）

```bash
cd /root/scholar-flow

# 仅检查参数与执行计划
scripts/validate-production-rollout.sh \
  --dry-run \
  --base-url "https://<your-backend-host>" \
  --admin-key "<ADMIN_API_KEY>" \
  --manuscript-id "<test-manuscript-uuid>"

# 完整执行：create run -> readiness -> regression -> finalize -> report
scripts/validate-production-rollout.sh \
  --base-url "https://<your-backend-host>" \
  --admin-key "<ADMIN_API_KEY>" \
  --manuscript-id "<test-manuscript-uuid>"

# 只跑 readiness（例如云端迁移刚完成时）
scripts/validate-production-rollout.sh \
  --base-url "https://<your-backend-host>" \
  --admin-key "<ADMIN_API_KEY>" \
  --readiness-only
```

退出码：
- `0`: GO（可放行）
- `1`: NO-GO（失败/阻塞/skip 不为 0）
- `2`: 参数或环境变量错误
- `3`: 运行时错误（网络/API/JQ 解析）

## 4. 手动 API 流程（调试用）

```bash
BASE_URL="https://<your-backend-host>"
ADMIN_KEY="<ADMIN_API_KEY>"
MANUSCRIPT_ID="<test-manuscript-uuid>"

# 1) 创建验收批次
RUN_ID=$(curl -s -X POST "$BASE_URL/api/v1/internal/release-validation/runs" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"feature_key\":\"042-production-pipeline\",\"environment\":\"staging\",\"manuscript_id\":\"$MANUSCRIPT_ID\"}" \
  | jq -r '.run.id')

# 2) 执行 readiness checks
curl -s -X POST "$BASE_URL/api/v1/internal/release-validation/runs/$RUN_ID/readiness" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"strict_blocking":true}'

# 3) 执行 regression checks（要求关键场景 skip=0）
curl -s -X POST "$BASE_URL/api/v1/internal/release-validation/runs/$RUN_ID/regression" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"require_zero_skip":true}'

# 4) 汇总结论
curl -s -X POST "$BASE_URL/api/v1/internal/release-validation/runs/$RUN_ID/finalize" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'

# 5) 读取完整报告
curl -s "$BASE_URL/api/v1/internal/release-validation/runs/$RUN_ID/report" \
  -H "X-Admin-Key: $ADMIN_KEY" | jq
```

## 5. 回归测试（本地）

```bash
cd /root/scholar-flow/backend
pytest -o addopts= \
  tests/unit/test_release_validation_service.py \
  tests/integration/test_release_validation_api.py \
  tests/contract/test_api_paths.py
```

## 6. 放行判定

只有同时满足以下条件才能放行：

1. readiness 阶段阻塞项为 0。
2. regression 关键场景无 skip。
3. 最终报告 `release_decision=go`。
4. 若判定 `no-go`，需执行并记录回退流程后再进入下一轮验收。

## 7. 实施验证记录（2026-02-09）

- 后端验证：
  - 命令：`pytest -o addopts= tests/unit/test_release_validation_service.py tests/integration/test_release_validation_api.py tests/contract/test_api_paths.py`
  - 结果：`15 passed`
- 脚本 dry-run：
  - 命令：`scripts/validate-production-rollout.sh --dry-run --base-url http://127.0.0.1:18080 --admin-key demo-key --manuscript-id 00000000-0000-0000-0000-000000000042`
  - 结果：输出 5 步执行计划，无错误退出（0）
- 脚本 real-run（mock backend）：
  - 关键输出：`readiness status=passed`、`regression status=passed skipped=0`、`release_decision=go`、`result: GO`
