#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/platform.env}"
HF_SPACE_REPO="${HF_SPACE_REPO:-LouisShawn/scholarflow-api}"
VERCEL_CWD="${VERCEL_CWD:-${ROOT_DIR}/frontend}"
VERCEL_TARGETS="${VERCEL_TARGETS:-production}"

APPLY_HF=1
APPLY_VERCEL=1
RESTART_HF=1
DEPLOY_VERCEL=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
用法:
  scripts/sync-platform-env.sh [options]

选项:
  --env-file <path>        环境变量文件（默认: deploy/platform.env）
  --hf-space <repo>        HF Space repo（默认: LouisShawn/scholarflow-api）
  --vercel-cwd <path>      Vercel 项目目录（默认: frontend）
  --vercel-targets <list>  目标环境，逗号分隔（默认: production）
                           可选: production,preview,development
  --hf-only                仅同步 Hugging Face
  --vercel-only            仅同步 Vercel
  --no-restart-hf          同步后不重启 HF Space
  --deploy-vercel          同步后执行 vercel --prod 部署
  --dry-run                仅打印计划，不实际写入
  -h, --help               显示帮助

依赖:
  - 已登录 hf CLI（hf auth login）
  - 已登录 vercel CLI（vercel login）

推荐流程:
  1) 复制 scripts/platform-env.example -> deploy/platform.env
  2) 填入真实值
  3) 先 dry-run: scripts/sync-platform-env.sh --dry-run
  4) 正式执行: scripts/sync-platform-env.sh
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --hf-space)
      HF_SPACE_REPO="${2:-}"
      shift 2
      ;;
    --vercel-cwd)
      VERCEL_CWD="${2:-}"
      shift 2
      ;;
    --vercel-targets)
      VERCEL_TARGETS="${2:-}"
      shift 2
      ;;
    --hf-only)
      APPLY_HF=1
      APPLY_VERCEL=0
      shift
      ;;
    --vercel-only)
      APPLY_HF=0
      APPLY_VERCEL=1
      shift
      ;;
    --no-restart-hf)
      RESTART_HF=0
      shift
      ;;
    --deploy-vercel)
      DEPLOY_VERCEL=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[sync-env] unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[sync-env] missing command: $1" >&2
    exit 2
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[sync-env] env file not found: $ENV_FILE" >&2
  echo "[sync-env] 先复制 scripts/platform-env.example 到该路径并填值。" >&2
  exit 2
fi

load_env_file() {
  local file="$1"
  while IFS= read -r line || [[ -n "$line" ]]; do
    # 去掉行首空白
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" ]] && continue
    [[ "$line" == \#* ]] && continue
    [[ "$line" != *=* ]] && continue

    # 支持 export KEY=VALUE
    if [[ "$line" == export\ * ]]; then
      line="${line#export }"
    fi

    local key="${line%%=*}"
    local raw="${line#*=}"

    # key 去空白
    key="$(echo "$key" | xargs)"
    [[ -z "$key" ]] && continue
    [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && continue

    # value: 仅去前后空白；若成对引号则剥离
    raw="${raw#"${raw%%[![:space:]]*}"}"
    raw="${raw%"${raw##*[![:space:]]}"}"
    if [[ "$raw" == \"*\" && "$raw" == *\" ]]; then
      raw="${raw:1:${#raw}-2}"
    elif [[ "$raw" == \'*\' && "$raw" == *\' ]]; then
      raw="${raw:1:${#raw}-2}"
    fi

    export "${key}=${raw}"
  done < "$file"
}

load_env_file "$ENV_FILE"

hf_secret_keys=(
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  SUPABASE_JWT_SECRET
  ADMIN_API_KEY
  MAGIC_LINK_JWT_SECRET
  CROSSREF_DEPOSITOR_EMAIL
  CROSSREF_DEPOSITOR_PASSWORD
  SMTP_USER
  SMTP_PASSWORD
  RESEND_API_KEY
  SENTRY_DSN
)

hf_variable_keys=(
  FRONTEND_ORIGIN
  FRONTEND_ORIGINS
  FRONTEND_BASE_URL
  GO_ENV
  APP_ENV
  SENTRY_ENABLED
  SENTRY_ENVIRONMENT
  SENTRY_TRACES_SAMPLE_RATE
  PRODUCTION_GATE_ENABLED
  PLAGIARISM_CHECK_ENABLED
  PLAGIARISM_SIMILARITY_THRESHOLD
  PLAGIARISM_POLL_MAX_ATTEMPTS
  PLAGIARISM_POLL_INTERVAL_SEC
  PLAGIARISM_SUBMIT_DELAY_SEC
  CROSSREF_DOI_PREFIX
  CROSSREF_API_URL
  CROSSREF_API_KEY
  MATCHMAKING_WARMUP
  MATCHMAKING_LOCAL_FILES_ONLY
  JOURNAL_SCOPE_ENFORCEMENT
  EMAIL_SENDER
)

vercel_public_keys=(
  NEXT_PUBLIC_API_URL
  BACKEND_ORIGIN
  NEXT_PUBLIC_SUPABASE_URL
  NEXT_PUBLIC_SUPABASE_ANON_KEY
  NEXT_PUBLIC_APP_ENV
  NEXT_PUBLIC_SENTRY_DSN
  NEXT_PUBLIC_SENTRY_ENVIRONMENT
)

vercel_secret_keys=(
  SENTRY_DSN
  SENTRY_AUTH_TOKEN
  SENTRY_ORG
  SENTRY_PROJECT
)

required_keys=(
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  FRONTEND_ORIGIN
  NEXT_PUBLIC_API_URL
  NEXT_PUBLIC_SUPABASE_URL
  NEXT_PUBLIC_SUPABASE_ANON_KEY
)

for key in "${required_keys[@]}"; do
  val="${!key:-}"
  if [[ -z "$val" ]]; then
    echo "[sync-env] required key is empty: $key" >&2
    exit 2
  fi
done

join_by_comma() {
  local IFS=","
  echo "$*"
}

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[sync-env] DRY RUN"
  echo "- ENV_FILE: $ENV_FILE"
  echo "- HF_SPACE_REPO: $HF_SPACE_REPO"
  echo "- VERCEL_CWD: $VERCEL_CWD"
  echo "- VERCEL_TARGETS: $VERCEL_TARGETS"
  echo "- APPLY_HF: $APPLY_HF"
  echo "- APPLY_VERCEL: $APPLY_VERCEL"
  echo "- RESTART_HF: $RESTART_HF"
  echo "- DEPLOY_VERCEL: $DEPLOY_VERCEL"

  if [[ "$APPLY_HF" -eq 1 ]]; then
    echo "[sync-env] HF secrets (only set non-empty):"
    for k in "${hf_secret_keys[@]}"; do
      [[ -n "${!k:-}" ]] && echo "  - $k"
    done
    echo "[sync-env] HF variables (only set non-empty):"
    for k in "${hf_variable_keys[@]}"; do
      [[ -n "${!k:-}" ]] && echo "  - $k"
    done
  fi

  if [[ "$APPLY_VERCEL" -eq 1 ]]; then
    echo "[sync-env] Vercel public env (only set non-empty):"
    for k in "${vercel_public_keys[@]}"; do
      [[ -n "${!k:-}" ]] && echo "  - $k"
    done
    echo "[sync-env] Vercel secret env (only set non-empty):"
    for k in "${vercel_secret_keys[@]}"; do
      [[ -n "${!k:-}" ]] && echo "  - $k"
    done
  fi

  exit 0
fi

if [[ "$APPLY_HF" -eq 1 ]]; then
  require_cmd python
  require_cmd hf

  if ! hf auth whoami >/dev/null 2>&1; then
    echo "[sync-env] hf 未登录，请先执行: hf auth login" >&2
    exit 2
  fi

  export HF_SPACE_REPO
  export HF_RESTART_AFTER_SYNC="$RESTART_HF"
  export HF_SECRET_KEYS="$(join_by_comma "${hf_secret_keys[@]}")"
  export HF_VARIABLE_KEYS="$(join_by_comma "${hf_variable_keys[@]}")"

  python - <<'PY'
import os
from huggingface_hub import HfApi

repo = os.environ["HF_SPACE_REPO"].strip()
restart = os.environ.get("HF_RESTART_AFTER_SYNC", "1").strip() == "1"
secret_keys = [x.strip() for x in os.environ.get("HF_SECRET_KEYS", "").split(",") if x.strip()]
var_keys = [x.strip() for x in os.environ.get("HF_VARIABLE_KEYS", "").split(",") if x.strip()]

api = HfApi(token=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN") or None)

synced_secrets = 0
synced_vars = 0

for key in secret_keys:
    value = os.environ.get(key, "")
    if not value:
        continue
    api.add_space_secret(repo_id=repo, key=key, value=value)
    print(f"[sync-env][hf] secret synced: {key}")
    synced_secrets += 1

for key in var_keys:
    value = os.environ.get(key, "")
    if not value:
        continue
    api.add_space_variable(repo_id=repo, key=key, value=value)
    print(f"[sync-env][hf] variable synced: {key}")
    synced_vars += 1

if restart:
    api.restart_space(repo_id=repo)
    print(f"[sync-env][hf] space restarted: {repo}")

print(f"[sync-env][hf] done: secrets={synced_secrets}, variables={synced_vars}")
PY
fi

if [[ "$APPLY_VERCEL" -eq 1 ]]; then
  require_cmd vercel

  if ! vercel whoami --cwd "$VERCEL_CWD" >/dev/null 2>&1; then
    echo "[sync-env] vercel 未登录，请先执行: vercel login" >&2
    exit 2
  fi

  IFS=',' read -r -a targets <<< "$VERCEL_TARGETS"

  upsert_vercel_env() {
    local key="$1"
    local value="$2"
    local target="$3"
    local sensitive_flag="$4"

    if [[ -z "$value" ]]; then
      return 0
    fi

    if printf '%s' "$value" | vercel env update "$key" "$target" --cwd "$VERCEL_CWD" --yes $sensitive_flag >/dev/null 2>&1; then
      echo "[sync-env][vercel][$target] updated: $key"
      return 0
    fi

    printf '%s' "$value" | vercel env add "$key" "$target" --cwd "$VERCEL_CWD" --yes $sensitive_flag >/dev/null
    echo "[sync-env][vercel][$target] added: $key"
  }

  for target in "${targets[@]}"; do
    t="$(echo "$target" | xargs)"
    [[ -z "$t" ]] && continue

    for key in "${vercel_public_keys[@]}"; do
      upsert_vercel_env "$key" "${!key:-}" "$t" ""
    done

    for key in "${vercel_secret_keys[@]}"; do
      upsert_vercel_env "$key" "${!key:-}" "$t" "--sensitive"
    done
  done

  if [[ "$DEPLOY_VERCEL" -eq 1 ]]; then
    vercel --cwd "$VERCEL_CWD" --prod --yes
    echo "[sync-env][vercel] production deployment triggered"
  fi
fi

echo "[sync-env] all done"
