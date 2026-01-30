import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL", "")
# 中文注释:
# - 历史原因：项目里同时存在 SUPABASE_KEY 与 SUPABASE_ANON_KEY（两者在多数环境下等价）。
# - 为保证兼容性，优先读 SUPABASE_ANON_KEY，缺省时回退到 SUPABASE_KEY。
key: str = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY") or ""

service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# === 统一 Supabase 客户端 ===
# 中文注释:
# 1. 遵循 v1.7.0 章程，使用真实凭证连接数据库。
# 2. 这里的 Client 将在所有 API 路由中共享。
supabase: Client = create_client(url, key)

# === 管理端 Supabase 客户端（用于服务端写入/内部任务） ===
# 中文注释:
# 1. notifications 表通常会启用 RLS 且限制 INSERT；后端写入需要 service role。
# 2. 若未配置 SUPABASE_SERVICE_ROLE_KEY，则回退为普通 key（开发环境可用），但生产环境请务必配置。
supabase_admin: Client = create_client(url, service_role_key or key)


def create_user_supabase_client(access_token: str) -> Client:
    """
    以“当前用户”身份调用 PostgREST（用于触发/验证 RLS）。

    中文注释:
    - 不能在全局 supabase 实例上调用 postgrest.auth(token)，会造成并发请求串号。
    - 因此为每个请求创建一个轻量 client，并注入当前用户 JWT。
    """

    client = create_client(url, key)
    client.postgrest.auth(access_token)
    return client
