#!/bin/bash

# 识别未覆盖路径（包装器）
# 用法: ./scripts/identify-uncovered.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${SCRIPT_DIR}/coverage/identify-uncovered.sh"
