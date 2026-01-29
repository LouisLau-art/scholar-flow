#!/bin/bash

# 覆盖率摘要（包装器）
# 用法: ./scripts/coverage-summary.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${SCRIPT_DIR}/coverage/summary.sh"
