import os
from supabase import create_client, Client
from app.core.config import app_config
from typing import Any, Optional, Callable

# Use configuration from AppConfig (Feature 019 support for staging)
url: str = app_config.supabase_url
# Legacy fallback logic preserved but using app_config values where possible
# Note: app_config loads SUPABASE_URL. Keys are still loaded from env directly here
# but ideally should move to config. for minimal disruption, we keep env reads for keys
# but ensure URL comes from our unified config which handles staging logic.

# 中文注释:
# - 历史原因：项目里同时存在 SUPABASE_KEY 与 SUPABASE_ANON_KEY（两者在多数环境下等价）。
# - 为保证兼容性，优先读 SUPABASE_ANON_KEY，缺省时回退到 SUPABASE_KEY。
key: str = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY") or ""

service_role_key: str = app_config.supabase_key or os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", ""
)

class _LazySupabaseClient:
    """
    延迟初始化 Supabase Client，避免在 import 时因为缺少环境变量导致整个模块导入失败。

    中文注释:
    - 单元测试会 patch `supabase`/`supabase_admin`，因此这里必须保证“可导入”。
    - 真实运行时，如果缺少 URL/KEY，在第一次访问 client 时抛出清晰错误即可。
    """

    def __init__(self, factory: Callable[[], Client], *, name: str):
        self._factory = factory
        self._name = name
        self._client: Optional[Client] = None

    def _get(self) -> Client:
        if self._client is None:
            self._client = self._factory()
        return self._client

    def __getattr__(self, item: str) -> Any:
        return getattr(self._get(), item)


def _require_supabase_url() -> str:
    if not url:
        raise RuntimeError("SUPABASE_URL is required")
    return url


def _require_anon_key() -> str:
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY or SUPABASE_KEY is required")
    return key


def _create_supabase() -> Client:
    return create_client(_require_supabase_url(), _require_anon_key())


def _create_supabase_admin() -> Client:
    admin_key = service_role_key or key
    if not admin_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) is required")
    return create_client(_require_supabase_url(), admin_key)


# === 统一 Supabase 客户端（延迟初始化） ===
supabase: Client = _LazySupabaseClient(_create_supabase, name="supabase")  # type: ignore[assignment]

# === 管理端 Supabase 客户端（延迟初始化） ===
supabase_admin: Client = _LazySupabaseClient(_create_supabase_admin, name="supabase_admin")  # type: ignore[assignment]


def create_user_supabase_client(access_token: str) -> Client:
    """
    以“当前用户”身份调用 PostgREST（用于触发/验证 RLS）。

    中文注释:
    - 不能在全局 supabase 实例上调用 postgrest.auth(token)，会造成并发请求串号。
    - 因此为每个请求创建一个轻量 client，并注入当前用户 JWT。
    """

    client = create_client(_require_supabase_url(), _require_anon_key())
    client.postgrest.auth(access_token)
    return client
