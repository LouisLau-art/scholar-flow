#!/bin/bash

# 生成测试覆盖率报告（包装器）
# 用法: ./scripts/generate-coverage-report.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${SCRIPT_DIR}/coverage/generate-report.sh"
