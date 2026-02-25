#!/usr/bin/env bash

set -euo pipefail

OUT=""
ENVIRONMENT="${ENVIRONMENT:-staging}"
SAMPLE_SET_ID="${SAMPLE_SET_ID:-editor-perf-v1}"
CAPTURED_BY="${CAPTURED_BY:-${USER:-unknown}}"
SCENARIO="${SCENARIO:-editor_detail}"
P50="${P50_INTERACTIVE_MS:-0}"
P95="${P95_INTERACTIVE_MS:-0}"
REQ_COUNT="${FIRST_SCREEN_REQUEST_COUNT:-0}"
NOTES="${NOTES:-}"

AUTO_URL=""
AUTO_TOKEN="${AUTO_TOKEN:-}"
AUTO_SAMPLES="${AUTO_SAMPLES:-10}"
AUTO_TIMEOUT_SEC="${AUTO_TIMEOUT_SEC:-15}"
AUTO_METHOD="${AUTO_METHOD:-GET}"
AUTO_JSON_BODY="${AUTO_JSON_BODY:-}"
AUTO_HEADERS_RAW=""

usage() {
  cat <<'USAGE'
Usage: scripts/perf/capture-editor-baseline.sh --output <path> [options]

Manual mode:
  直接传入 p50/p95/requests。

Auto probe mode:
  提供 --auto-url 后，脚本会自动采样 API TTFB（time-to-first-byte）并回填 p50/p95。

Options:
  --output <path>         Output JSON path (required)
  --environment <value>   staging | local-ci (default: staging)
  --sample-set <value>    Sample set id (default: editor-perf-v1)
  --captured-by <value>   Operator id/name
  --scenario <value>      editor_detail | editor_process | editor_workspace | reviewer_search_repeat
  --p50 <ms>              p50 interactive time (manual mode)
  --p95 <ms>              p95 interactive time (manual mode)
  --requests <count>      First screen request count
  --notes <text>          Optional notes

Auto probe:
  --auto-url <url>        API URL for sampling
  --token <bearer>        Optional Bearer token
  --samples <count>       Probe sample count (default: 10)
  --timeout-sec <sec>     Per request timeout (default: 15)
  --method <verb>         HTTP method (default: GET)
  --json-body <json>      Optional JSON body for probe request
  --header <k:v>          Extra HTTP header (repeatable)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUT="${2:-}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="${2:-}"
      shift 2
      ;;
    --sample-set)
      SAMPLE_SET_ID="${2:-}"
      shift 2
      ;;
    --captured-by)
      CAPTURED_BY="${2:-}"
      shift 2
      ;;
    --scenario)
      SCENARIO="${2:-}"
      shift 2
      ;;
    --p50)
      P50="${2:-0}"
      shift 2
      ;;
    --p95)
      P95="${2:-0}"
      shift 2
      ;;
    --requests)
      REQ_COUNT="${2:-0}"
      shift 2
      ;;
    --notes)
      NOTES="${2:-}"
      shift 2
      ;;
    --auto-url)
      AUTO_URL="${2:-}"
      shift 2
      ;;
    --token)
      AUTO_TOKEN="${2:-}"
      shift 2
      ;;
    --samples)
      AUTO_SAMPLES="${2:-10}"
      shift 2
      ;;
    --timeout-sec)
      AUTO_TIMEOUT_SEC="${2:-15}"
      shift 2
      ;;
    --method)
      AUTO_METHOD="${2:-GET}"
      shift 2
      ;;
    --json-body)
      AUTO_JSON_BODY="${2:-}"
      shift 2
      ;;
    --header)
      if [[ -n "${AUTO_HEADERS_RAW}" ]]; then
        AUTO_HEADERS_RAW="${AUTO_HEADERS_RAW}"$'\n'"${2:-}"
      else
        AUTO_HEADERS_RAW="${2:-}"
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$OUT" ]]; then
  echo "--output is required" >&2
  usage
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

python3 - <<'PY' \
  "$OUT" "$ENVIRONMENT" "$SAMPLE_SET_ID" "$CAPTURED_BY" "$SCENARIO" \
  "$P50" "$P95" "$REQ_COUNT" "$NOTES" \
  "$AUTO_URL" "$AUTO_TOKEN" "$AUTO_SAMPLES" "$AUTO_TIMEOUT_SEC" "$AUTO_METHOD" "$AUTO_JSON_BODY" "$AUTO_HEADERS_RAW"
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

(
    out,
    environment,
    sample_set_id,
    captured_by,
    scenario,
    p50_raw,
    p95_raw,
    req_count_raw,
    notes_raw,
    auto_url,
    auto_token,
    auto_samples_raw,
    auto_timeout_raw,
    auto_method_raw,
    auto_json_body,
    auto_headers_raw,
) = sys.argv[1:]


def to_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def percentile(values: list[int], p: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1)))))
    return int(ordered[idx])


p50 = to_int(p50_raw, 0)
p95 = to_int(p95_raw, 0)
req_count = to_int(req_count_raw, 0)
notes = notes_raw.strip()

if auto_url.strip():
    samples = max(1, to_int(auto_samples_raw, 10))
    timeout_sec = max(1, to_int(auto_timeout_raw, 15))
    auto_method = (auto_method_raw or "GET").strip().upper() or "GET"
    header_rows = [line.strip() for line in (auto_headers_raw or "").splitlines() if line.strip()]
    body_bytes = auto_json_body.encode("utf-8") if auto_json_body else None
    measurements: list[int] = []
    failures: list[str] = []

    for i in range(samples):
        req = urllib.request.Request(auto_url, method=auto_method, data=body_bytes)
        if auto_token:
            req.add_header("Authorization", f"Bearer {auto_token}")
        if body_bytes is not None:
            req.add_header("Content-Type", "application/json")
        for header in header_rows:
            if ":" not in header:
                continue
            k, v = header.split(":", 1)
            req.add_header(k.strip(), v.strip())

        started_at = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                _ = response.status
        except urllib.error.HTTPError as e:
            _ = e.code
        except Exception as e:  # noqa: BLE001
            failures.append(f"sample#{i + 1}:{e}")
            continue
        elapsed_ms = max(1, int(round((time.perf_counter() - started_at) * 1000)))
        measurements.append(elapsed_ms)

    if not measurements:
        raise SystemExit(
            f"[capture-editor-baseline] auto probe failed: no successful sample for {auto_url}; failures={len(failures)}"
        )

    if p50 <= 0:
        p50 = percentile(measurements, 50)
    if p95 <= 0:
        p95 = percentile(measurements, 95)
    if req_count <= 0:
        req_count = 1

    auto_summary = {
        "probe_mode": "api_ttfb",
        "url": auto_url,
        "method": auto_method,
        "samples": len(measurements),
        "failed_samples": len(failures),
        "ttfb_min_ms": min(measurements),
        "ttfb_max_ms": max(measurements),
        "ttfb_mean_ms": round(statistics.fmean(measurements), 2),
    }
    notes = f"{notes} | {json.dumps(auto_summary, ensure_ascii=True)}".strip(" |")

if p50 <= 0 or p95 <= 0 or req_count <= 0:
    raise SystemExit("[capture-editor-baseline] p50/p95/requests must all be > 0")

payload = {
    "environment": environment,
    "sample_set_id": sample_set_id,
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "captured_by": captured_by,
    "records": [
        {
            "scenario": scenario,
            "p50_interactive_ms": int(p50),
            "p95_interactive_ms": int(p95),
            "first_screen_request_count": int(req_count),
            "notes": notes or None,
        }
    ],
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=True, indent=2)
    f.write("\n")
PY

echo "[capture-editor-baseline] wrote $OUT"
