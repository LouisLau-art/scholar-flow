#!/bin/bash

# 清理测试数据（依赖 SUPABASE_URL / SUPABASE_KEY）
# 用法: ./scripts/cleanup-test-data.sh

set -e

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "⚠️  SUPABASE_URL 或 SUPABASE_KEY 未设置，跳过清理"
    exit 0
fi

python3 - <<'PY'
import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
client = create_client(url, key)

test_author_id = "00000000-0000-0000-0000-000000000000"

try:
    res = client.table("manuscripts").delete().eq("author_id", test_author_id).execute()
    count = len(res.data) if res and res.data else 0
    print(f"✅ 已清理 manuscripts 测试数据: {count} 条")
except Exception as exc:
    print(f"⚠️  清理 manuscripts 失败: {exc}")
PY
