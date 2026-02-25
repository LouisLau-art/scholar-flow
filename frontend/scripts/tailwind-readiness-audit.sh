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

if [[ "${TAILWIND_AUDIT_ENFORCE:-0}" == "1" ]]; then
  max_w96="${TAILWIND_MAX_W96:-0}"
  max_hex="${TAILWIND_MAX_HEX:-0}"
  max_inline="${TAILWIND_MAX_INLINE_STYLE:-0}"
  max_hard_palette="${TAILWIND_MAX_HARD_PALETTE:-0}"

  violations=()

  if (( count_w96 > max_w96 )); then
    violations+=("w-[96vw] expected <= ${max_w96}, got ${count_w96}")
  fi
  if (( count_hex > max_hex )); then
    violations+=("hex colors expected <= ${max_hex}, got ${count_hex}")
  fi
  if (( count_inline_style > max_inline )); then
    violations+=("inline style expected <= ${max_inline}, got ${count_inline_style}")
  fi
  if (( count_hard_palette > max_hard_palette )); then
    violations+=("hard palette expected <= ${max_hard_palette}, got ${count_hard_palette}")
  fi

  if ((${#violations[@]} > 0)); then
    echo
    echo "Tailwind readiness gate failed:"
    printf -- '- %s\n' "${violations[@]}"
    exit 1
  fi

  echo
  echo "Tailwind readiness gate passed."
fi
