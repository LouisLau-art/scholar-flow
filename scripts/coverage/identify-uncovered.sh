#!/bin/bash

# 识别未覆盖的代码路径
# 用法: ./scripts/coverage/identify-uncovered.sh

set -e

echo "🔍 识别未覆盖的代码路径"
echo "========================="
echo ""

# 检查后端覆盖率
if [ -f "backend/coverage.xml" ]; then
    echo "后端未覆盖文件:"
    echo "----------------"

    # 使用 coverage xml 解析未覆盖的文件
    if command -v python3 &> /dev/null; then
        python3 -c "
import xml.etree.ElementTree as ET
import os

tree = ET.parse('backend/coverage.xml')
root = tree.getroot()

uncovered_files = []
for package in root.findall('.//package'):
    for cls in package.findall('.//class'):
        filename = cls.get('filename')
        line_rate = float(cls.get('line-rate', 0))
        if line_rate < 1.0:
            uncovered_files.append((filename, line_rate))

if uncovered_files:
    for filename, rate in sorted(uncovered_files, key=lambda x: x[1]):
        print(f'  {filename}: {rate*100:.1f}% covered')
else:
    print('  ✅ 所有文件都已覆盖')
"
    else
        echo "  需要安装 Python 以解析覆盖率报告"
    fi
    echo ""
else
    echo "后端覆盖率报告未生成"
    echo ""
fi

# 检查前端覆盖率
if [ -f "frontend/coverage/coverage-summary.json" ]; then
    echo "前端未覆盖文件:"
    echo "----------------"

    if command -v python3 &> /dev/null; then
        python3 -c "
import json

with open('frontend/coverage/coverage-summary.json', 'r') as f:
    data = json.load(f)

uncovered_files = []
for file_path, metrics in data.get('total', {}).items():
    if file_path != 'total':
        line_rate = metrics.get('pct', 0)
        if line_rate < 100:
            uncovered_files.append((file_path, line_rate))

if uncovered_files:
    for filename, rate in sorted(uncovered_files, key=lambda x: x[1]):
        print(f'  {filename}: {rate:.1f}% covered')
else:
    print('  ✅ 所有文件都已覆盖')
"
    else
        echo "  需要安装 Python 以解析覆盖率报告"
    fi
    echo ""
elif [ -f "frontend/coverage/coverage-final.json" ]; then
    echo "前端未覆盖文件:"
    echo "----------------"

    if command -v python3 &> /dev/null; then
        python3 -c "
import json

with open('frontend/coverage/coverage-final.json', 'r') as f:
    data = json.load(f)

uncovered_files = []
for file_path, metrics in data.items():
    statements = metrics.get('s', {})
    total = len(statements)
    if total == 0:
        continue
    covered = sum(1 for count in statements.values() if count > 0)
    pct = (covered / total) * 100
    if pct < 100:
        uncovered_files.append((file_path, pct))

if uncovered_files:
    for filename, rate in sorted(uncovered_files, key=lambda x: x[1]):
        print(f'  {filename}: {rate:.1f}% covered')
else:
    print('  ✅ 所有文件都已覆盖')
"
    else
        echo "  需要安装 Python 以解析覆盖率报告"
    fi
    echo ""
else
    echo "前端覆盖率报告未生成"
    echo ""
fi

echo "💡 建议:"
echo "  1. 查看 HTML 报告获取详细信息"
echo "  2. 为未覆盖的代码添加测试用例"
echo "  3. 确保关键业务逻辑达到 100% 覆盖率"
