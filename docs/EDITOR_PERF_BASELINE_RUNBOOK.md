# Editor 性能基线采集手册

> 目的：统一采集 `/editor/manuscript/[id]`、`/editor/process`、`/editor/workspace`、`/editor/pipeline` 四条链路的 API TTFB 基线，便于改前改后量化对比。

## 1. 前置条件

- 后端可访问地址（例如 HF Space）：`BASE_URL`
- 一个可用 Bearer Token：`TOKEN`
- 一个真实稿件 ID（用于 detail 场景）：`MANUSCRIPT_ID`

示例（本地 shell）：

```bash
export BASE_URL="https://your-backend.example.com"
export TOKEN="your-bearer-token"
export MANUSCRIPT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## 2. 一次性采集四条链路基线

```bash
scripts/perf/capture-editor-api-baselines.sh \
  --base-url "$BASE_URL" \
  --token "$TOKEN" \
  --manuscript-id "$MANUSCRIPT_ID" \
  --samples 12 \
  --prefix baseline-2026-02-26 \
  --environment staging \
  --sample-set editor-perf-v1
```

输出位置（默认）：

- `specs/001-editor-performance-refactor/artifacts/baseline-2026-02-26-editor_detail.json`
- `specs/001-editor-performance-refactor/artifacts/baseline-2026-02-26-editor_process.json`
- `specs/001-editor-performance-refactor/artifacts/baseline-2026-02-26-editor_workspace.json`
- `specs/001-editor-performance-refactor/artifacts/baseline-2026-02-26-editor_pipeline.json`

## 3. 对比改前/改后结果

单场景对比示例（以 pipeline 为例）：

```bash
scripts/perf/compare-editor-baseline.sh \
  --before specs/001-editor-performance-refactor/artifacts/baseline-before-editor_pipeline.json \
  --after specs/001-editor-performance-refactor/artifacts/baseline-after-editor_pipeline.json \
  --output specs/001-editor-performance-refactor/artifacts/pipeline-summary.json
```

生成 Markdown 汇总：

```bash
scripts/perf/write-regression-report.sh \
  --summary specs/001-editor-performance-refactor/artifacts/pipeline-summary.json \
  --output specs/001-editor-performance-refactor/artifacts/pipeline-summary.md
```

## 4. 判读建议（MVP）

- 先看 `p95_interactive_ms`：优先反映“卡顿”体感。
- 再看 `first_screen_request_count`：请求数不下降时，TTFB 优化收益常被抵消。
- 同时看 `notes` 里的 `ttfb_mean_ms/ttfb_max_ms`：可快速识别偶发长尾。
