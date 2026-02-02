#!/usr/bin/env python3
"""
为开发/演示环境回填 manuscripts.file_path（缺失 PDF 时导致 reviewer 预览 404）。

默认行为：
- 找出 file_path 为空的稿件（可按 status 过滤）
- 将本地一个占位 PDF 上传到 Supabase Storage bucket=manuscripts
- 更新 manuscripts.file_path 指向上传路径

用法：
  python scripts/backfill_missing_manuscript_pdfs.py
  python scripts/backfill_missing_manuscript_pdfs.py --pdf ./test_manuscript.pdf --limit 50
  python scripts/backfill_missing_manuscript_pdfs.py --statuses under_review,submitted
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from supabase import create_client


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _require(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"缺少环境变量 {name}（请检查 backend/.env 或 .env）")
    return v


def _split_statuses(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def _chunks(items: list[dict], size: int) -> Iterable[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="test_manuscript.pdf", help="本地占位 PDF 路径")
    parser.add_argument("--limit", type=int, default=50, help="最多回填多少条（默认 50）")
    parser.add_argument(
        "--statuses",
        default="under_review,submitted,resubmitted,revision_requested,pending_decision",
        help="仅处理这些状态（逗号分隔）",
    )
    args = parser.parse_args()

    # 允许从项目约定位置自动加载 env（避免每次手动 export）
    _load_env_file(Path(".env"))
    _load_env_file(Path("backend/.env"))

    url = _require("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not key:
        raise SystemExit("缺少 SUPABASE_SERVICE_ROLE_KEY（建议使用 service_role 做回填）")

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"找不到 PDF 文件：{pdf_path}")
    pdf_bytes = pdf_path.read_bytes()

    statuses = _split_statuses(args.statuses)
    client = create_client(url, key)

    # 找出 file_path 为空的稿件
    q = client.table("manuscripts").select("id,status,file_path,title").is_("file_path", "null").limit(args.limit)
    if statuses:
        q = q.in_("status", statuses)
    rows = q.execute().data or []

    if not rows:
        print("无需回填：没有符合条件的 manuscripts.file_path 为空的记录")
        return

    print(f"准备回填 {len(rows)} 条稿件的 file_path（bucket=manuscripts，占位 PDF={pdf_path}）")

    bucket = client.storage.from_("manuscripts")
    updated = 0
    for r in rows:
        mid = r["id"]
        dest = f"mock/{mid}.pdf"
        try:
            bucket.upload(dest, pdf_bytes, {"content-type": "application/pdf", "upsert": "true"})
            client.table("manuscripts").update({"file_path": dest}).eq("id", mid).execute()
            updated += 1
            print(f"- OK {mid} -> {dest}")
        except Exception as e:
            print(f"- FAIL {mid}: {e}")

    print(f"完成：成功回填 {updated}/{len(rows)} 条")


if __name__ == "__main__":
    main()

