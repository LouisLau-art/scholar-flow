#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGETS=(src/app src/components src/pages)

count_matches() {
  local pattern="$1"
  (rg -o "$pattern" "${TARGETS[@]}" 2>/dev/null || true) | wc -l | tr -d ' '
}

count_w96="$(count_matches 'w-\[96vw\]')"
count_hex="$(count_matches '#[0-9a-fA-F]{3,8}')"
count_inline_style="$(count_matches 'style=\{\{')"
count_hard_palette="$(count_matches '(bg|text|border)-(slate|blue)-')"
count_magic_width="$(count_matches 'w-\[[0-9]+(px|vw|vh|rem)\]')"

echo "Tailwind Readiness Audit"
echo "========================"
echo "Targets: ${TARGETS[*]}"
echo
echo "Core counters"
echo "- w-[96vw]                        : $count_w96"
echo "- hex colors (#xxxxxx)           : $count_hex"
echo "- inline style={{...}}           : $count_inline_style"
echo "- hard palette (slate/blue)      : $count_hard_palette"
echo "- magic width tokens (w-[...])   : $count_magic_width"
echo
echo "Top files: hard palette usage"
(rg -n '(bg|text|border)-(slate|blue)-' "${TARGETS[@]}" || true) \
  | cut -d: -f1 \
  | sort \
  | uniq -c \
  | sort -nr \
  | head -n 10
echo
echo "Top files: inline style usage"
(rg -n 'style=\{\{' "${TARGETS[@]}" || true) \
  | cut -d: -f1 \
  | sort \
  | uniq -c \
  | sort -nr \
  | head -n 10
