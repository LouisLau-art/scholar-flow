# Tier-1 / Tier-2 Validation Log

## 执行时间
- 2026-02-24

## Command 1: Frontend 定向性能/缓存回归
```bash
cd frontend && bun run test -- --run \
  src/components/ReviewerAssignModal.test.tsx \
  src/services/__tests__/editorApi.reviewer-library-cache.test.ts \
  src/components/editor/__tests__/audit-log-timeline.performance.test.tsx \
  src/components/editor/__tests__/manuscripts-process-panel.performance.test.tsx \
  src/pages/editor/workspace/__tests__/page.performance.test.tsx \
  src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx \
  src/components/editor/__tests__/internal-notebook-mentions.test.tsx
```

结果摘要：
- `Test Files: 7 passed`
- `Tests: 16 passed`
- 备注：`ReviewerAssignModal.test.tsx` 存在 Radix Select 的 `act(...)` warning，但不影响通过。

## Command 2: Backend 定向集成回归
```bash
cd backend && pytest -o addopts= \
  tests/integration/test_editor_invite.py \
  tests/integration/test_reviewer_library.py \
  tests/integration/test_editor_timeline.py \
  tests/integration/test_internal_collaboration_flow.py \
  tests/integration/test_release_validation_gate.py
```

结果摘要：
- `13 passed`
- warning：dateutil/importlib metadata deprecation（不影响通过）

## Command 3: Feature 性能门禁脚本
```bash
scripts/validate-editor-performance.sh
```

结果摘要：
- 生成 `baseline-compare.json` 与 `regression-report.md`
- 门禁结论：`GO`（全部场景无回退，最差 regression ratio = `0.0`）
