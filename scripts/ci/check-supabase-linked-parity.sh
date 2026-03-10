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

if grep -q "Remote database is up to date" <<<"${dry_run_output}"; then
  echo "[supabase-parity] remote database is up to date"
  exit 0
fi

echo "[supabase-parity] pending migration drift detected" >&2
exit 1
