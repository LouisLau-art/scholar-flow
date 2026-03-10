#!/usr/bin/env bash

set -euo pipefail

PROJECT_REF="${SUPABASE_PROJECT_REF:-}"
DB_PASSWORD="${SUPABASE_DB_PASSWORD:-}"
ACCESS_TOKEN="${SUPABASE_ACCESS_TOKEN:-}"

usage() {
  cat <<'EOF'
Usage: scripts/ci/check-supabase-linked-parity.sh

Required environment variables:
  SUPABASE_ACCESS_TOKEN
  SUPABASE_PROJECT_REF
  SUPABASE_DB_PASSWORD
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${ACCESS_TOKEN}" || -z "${PROJECT_REF}" || -z "${DB_PASSWORD}" ]]; then
  usage >&2
  exit 2
fi

if ! command -v supabase >/dev/null 2>&1; then
  echo "[supabase-parity] missing dependency: supabase CLI" >&2
  exit 2
fi

echo "[supabase-parity] authenticating CLI"
supabase login --token "${ACCESS_TOKEN}" >/dev/null

echo "[supabase-parity] linking project ${PROJECT_REF}"
supabase link --project-ref "${PROJECT_REF}" --password "${DB_PASSWORD}" >/dev/null

echo "[supabase-parity] collecting migration list"
migration_output="$(supabase migration list --linked 2>&1)"
echo "${migration_output}"

echo "[supabase-parity] running dry-run push"
dry_run_output="$(supabase db push --linked --dry-run 2>&1)"
echo "${dry_run_output}"

set +e
mismatch_report="$(
  MIGRATION_OUTPUT="${migration_output}" python - <<'PY'
import os
import sys

rows: list[tuple[str, str]] = []
for raw_line in os.environ.get("MIGRATION_OUTPUT", "").splitlines():
    line = raw_line.strip()
    if "|" not in line:
        continue
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 3:
        continue
    local_version, remote_version = parts[0], parts[1]
    if not local_version.isdigit() or len(local_version) != 14:
        continue
    if not remote_version.isdigit() or len(remote_version) != 14:
        continue
    rows.append((local_version, remote_version))

if not rows:
    print("Unable to parse `supabase migration list --linked` output", file=sys.stderr)
    sys.exit(2)

mismatches = [(local, remote) for local, remote in rows if local != remote]
if mismatches:
    print("mismatch")
    for local, remote in mismatches:
        print(f"{local or '-'} != {remote or '-'}")
    sys.exit(1)

print("ok")
PY
)"
parse_status=$?
set -e

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## Supabase Migration Parity"
    echo
    echo "- Project Ref: \`${PROJECT_REF}\`"
    echo
    echo "### migration list --linked"
    echo
    echo '```text'
    echo "${migration_output}"
    echo '```'
    echo
    echo "### db push --linked --dry-run"
    echo
    echo '```text'
    echo "${dry_run_output}"
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
fi

if [[ ${parse_status} -eq 0 && "${mismatch_report}" == "ok" ]]; then
  echo "[supabase-parity] remote database is up to date"
  exit 0
fi

echo "[supabase-parity] pending migration drift detected" >&2
echo "${mismatch_report}" >&2
exit 1
