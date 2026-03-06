from __future__ import annotations

import hashlib
import os
import re
import unicodedata


def sanitize_storage_filename(
    filename: str | None,
    *,
    default_name: str = "file",
    max_stem_len: int = 80,
) -> str:
    """
    规范化 Storage 对象文件名，避免 Supabase InvalidKey。

    中文注释:
    - 仅保留 ASCII 安全字符（字母/数字/._-）。
    - 去除路径分隔符，避免目录穿越/非法 key。
    - 当原始 stem 全为非 ASCII（如中文）时，退化为 default_name + hash，兼顾可读性与唯一性。
    """
    raw = str(filename or "").strip().replace("/", "_").replace("\\", "_")
    stem, ext = os.path.splitext(raw)
    stem = stem.strip().strip("._-")

    safe_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", safe_stem).strip("._-")

    if not safe_stem:
        if stem:
            digest = hashlib.sha1(stem.encode("utf-8", errors="ignore")).hexdigest()[:8]
            safe_stem = f"{default_name}_{digest}"
        else:
            safe_stem = default_name

    safe_stem = safe_stem[:max_stem_len].rstrip("._-") or default_name

    safe_ext = unicodedata.normalize("NFKD", ext).encode("ascii", "ignore").decode("ascii")
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", safe_ext).lower()
    if safe_ext and not safe_ext.startswith("."):
        safe_ext = f".{safe_ext}"
    if safe_ext == ".":
        safe_ext = ""
    if len(safe_ext) > 10:
        safe_ext = safe_ext[:10]

    return f"{safe_stem}{safe_ext}"

