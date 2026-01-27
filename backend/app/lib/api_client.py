import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_ANON_KEY", "")

# === 统一 Supabase 客户端 ===
# 中文注释:
# 1. 遵循 v1.7.0 章程，使用真实凭证连接数据库。
# 2. 这里的 Client 将在所有 API 路由中共享。
supabase: Client = create_client(url, key)
