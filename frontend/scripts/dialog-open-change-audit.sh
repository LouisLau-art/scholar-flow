#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Dialog onOpenChange Audit"
echo "=========================="

# 禁止在 onOpenChange 中显式写入 setXxx(true)，这会导致“关闭后瞬时重开”类问题。
risky_pattern='onOpenChange=\{\s*\([^)]*\)\s*=>[\s\S]{0,240}?set[A-Za-z0-9_]*\(\s*true\s*\)'

if rg -nUP "$risky_pattern" src >/tmp/dialog_audit_risky.txt; then
  echo "Found risky onOpenChange reopen patterns:"
  cat /tmp/dialog_audit_risky.txt
  echo
  echo "Fix guideline: keep onOpenChange close-only (nextOpen=false -> close)."
  exit 1
fi

direct_setter_count="$(rg -n "onOpenChange=\\{set[A-Za-z0-9_]+\\}" src | wc -l | tr -d '[:space:]')"
echo "Direct setter usage count (manual review recommended): ${direct_setter_count}"
echo "Dialog onOpenChange audit passed."
