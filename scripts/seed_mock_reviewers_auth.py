#!/usr/bin/env python3
"""
在云端 Supabase 创建“可用的 mock reviewers”（同时存在于 auth.users + public.user_profiles）

为什么需要这个脚本？
- 仅往 public.user_profiles 插入 mock 数据（id 不在 auth.users）会导致：
  - review_assignments.reviewer_id 外键失败（无法指派）
  - notifications.user_id 外键失败（无法给这些 mock 用户发站内信）
- 如果你希望 mock reviewer 真正能走完整工作流（被指派、看到任务、收到通知），
  必须创建对应的 Auth 用户。

使用方法（本地运行）：
  1) 确保 backend/.env 里有 SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
  2) 运行：
     python scripts/seed_mock_reviewers_auth.py --count 20 --domain mock.com

输出：
  - 会在控制台打印创建的 email + password（方便你用这些账号登录）
  - 默认会把 roles 设置为 ['reviewer']

注意：
  - 这会在 Supabase Auth 里创建真实用户，数量别太夸张（用于开发/演示即可）。
  - 如需清理，请在 Supabase Dashboard → Auth → Users 删除这些用户。
"""

from __future__ import annotations

import argparse
import os
import secrets
import string
from dataclasses import dataclass
from typing import Dict, List

from supabase import create_client


@dataclass(frozen=True)
class CreatedUser:
    email: str
    password: str
    user_id: str


def _rand_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _require_env(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val:
        raise SystemExit(f"Missing required env var: {name}")
    return val


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--domain", type=str, default="mock.com")
    ap.add_argument("--prefix", type=str, default="reviewer")
    ap.add_argument("--role", type=str, default="reviewer")
    ap.add_argument("--password", type=str, default="", help="Optional fixed password for all users")
    args = ap.parse_args()

    url = _require_env("SUPABASE_URL")
    service_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")

    client = create_client(url, service_key)
    admin = client.auth.admin

    created: List[CreatedUser] = []
    failures: List[str] = []

    for i in range(1, args.count + 1):
        email = f"{args.prefix}{i}@{args.domain}"
        full_name = f"Mock Reviewer {i}"
        password = args.password or _rand_password()

        user_id = None
        try:
            resp = admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name},
                }
            )
            user = getattr(resp, "user", None)
            if user is None:
                raise RuntimeError("create_user returned no user")
            user_id = user.id
        except Exception as e:
            # 如果已存在，尝试从 list_users 里找 id
            msg = str(e).lower()
            if "already" in msg and ("exists" in msg or "registered" in msg):
                try:
                    users = admin.list_users()
                    for u in users:
                        if (getattr(u, "email", "") or "").lower() == email.lower():
                            user_id = u.id
                            break
                except Exception as list_err:
                    failures.append(f"{email}: exists but cannot resolve id ({list_err})")
                    continue
            else:
                failures.append(f"{email}: create_user failed ({e})")
                continue

        if not user_id:
            failures.append(f"{email}: cannot determine user_id")
            continue

        # upsert user_profiles to make it visible in admin user list / reviewer pool
        try:
            client.table("user_profiles").upsert(
                {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "roles": [args.role],
                    "updated_at": "now()",
                }
            ).execute()
        except Exception as e:
            failures.append(f"{email}: upsert user_profiles failed ({e})")
            continue

        created.append(CreatedUser(email=email, password=password, user_id=user_id))

    print("\n=== Created/Updated Mock Reviewers ===")
    for u in created:
        print(f"- {u.email} | password={u.password} | id={u.user_id}")

    if failures:
        print("\n=== Failures ===")
        for f in failures:
            print(f"- {f}")


if __name__ == "__main__":
    main()

