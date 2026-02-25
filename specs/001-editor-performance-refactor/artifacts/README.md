# Artifacts Workspace

该目录用于存放 `001-editor-performance-refactor` 的性能与回归证据。

## 约定

- `baseline-before.json` / `baseline-after.json`: 改造前后基线数据。
- `baseline-*-api.json`: 自动采样 API TTFB 基线（detail/process/workspace）。
- `regression-report.md`: 回归门禁结论（GO / NO-GO）。
- `test-log-tier12.md` / `test-log-tier3.md`: 测试执行日志摘要。
- `feedback-metrics-plan.md` / `feedback-7day-report.md`: 7 天反馈指标计划与对比。
- `release-closure-checklist.md`: 发布收尾清单。

## 数据格式

基线 JSON 建议遵循同目录的 `baseline.schema.json`。
