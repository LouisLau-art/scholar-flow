from __future__ import annotations

from dataclasses import dataclass

from app.lib.api_client import supabase_admin


def _normalize_signed_url(resp: object) -> str | None:
    if not isinstance(resp, dict):
        return None
    return str(resp.get("signedUrl") or resp.get("signedURL") or "") or None


def ensure_bucket_exists(*, bucket: str, public: bool = False) -> None:
    """
    确保 Storage bucket 存在（开发/演示环境兜底）。

    中文注释:
    - 正式环境建议用 migration / Dashboard 创建 bucket。
    - 但为了减少“缺桶导致 500”的踩坑，这里做一次性兜底创建。
    """
    storage = getattr(supabase_admin, "storage", None)
    if storage is None or not hasattr(storage, "get_bucket") or not hasattr(storage, "create_bucket"):
        return

    try:
        storage.get_bucket(bucket)
        return
    except Exception:
        pass

    try:
        storage.create_bucket(bucket, options={"public": bool(public)})
    except Exception as e:
        text = str(e).lower()
        if "already" in text or "exists" in text or "duplicate" in text:
            return
        raise


@dataclass(frozen=True)
class SignedUrl:
    url: str
    expires_in: int


def create_signed_url(*, bucket: str, path: str, expires_in: int) -> SignedUrl:
    signed = supabase_admin.storage.from_(bucket).create_signed_url(path, expires_in)
    url = _normalize_signed_url(signed)
    if not url:
        raise RuntimeError("Failed to create signed url")
    return SignedUrl(url=url, expires_in=expires_in)


def upload_bytes(
    *,
    bucket: str,
    path: str,
    content: bytes,
    content_type: str,
    upsert: bool = True,
) -> None:
    ensure_bucket_exists(bucket=bucket, public=False)
    # storage3 期望 header value 为字符串；传 bool 会触发 httpx "Header value must be str or bytes"。
    opts = {"content-type": content_type, "upsert": "true" if upsert else "false"}
    supabase_admin.storage.from_(bucket).upload(path, content, opts)
