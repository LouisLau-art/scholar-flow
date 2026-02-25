# Editor Performance Triage Summary (2026-02-25)

## Scope
- Environment: `staging` (`https://scholar-flow-q1yw.vercel.app`)
- Key endpoint: `GET /api/v1/editor/manuscripts/{id}?skip_cards=true`
- Manuscript: `a36fa113-d011-4d46-b8ba-aa5662f20b58`

## Baseline vs Post-Deploy
- Baseline source: `triage-20260225-125731/prod-warm.json` (20 samples)
- Post-deploy source: `triage-20260225-optimized/prod-warm-editor_detail-postdeploy.json` (10 samples)

| Metric | Baseline | Post-Deploy | Delta |
| --- | ---: | ---: | ---: |
| `p50_interactive_ms` | 4138 | 2457 | -40.6% |
| `p95_interactive_ms` | 5341 | 2955 | -44.7% |

## Implemented Optimization (Main Branch)
- API split into lightweight + deferred-heavy path:
  - `skip_cards=true` now defaults to lightweight detail payload.
  - `include_heavy=true` explicitly loads heavy blocks (`files`, `reviewer_invites`, `revisions` context).
- Added short TTL cache for heavy blocks + force-refresh bypass (`x-sf-force-refresh`).
- Added revision query-variant capability cache to avoid repeated schema-fallback probes.
- Frontend detail page switched to:
  - core-first lightweight load;
  - async deferred heavy-context merge;
  - force-refresh after mutating actions.

## Verification Snapshot
- Live API check after deploy:
  - `is_deferred_context_loaded=false`
  - `files_len=1`
  - `reviewer_invites_len=0`
  - `author_response_history_len=0`

