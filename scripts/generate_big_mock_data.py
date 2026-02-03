import random
import uuid

def generate_sql():
    # 核心逻辑：使用 SQL 变量动态获取当前真实存在的用户 ID
    sql_output = [
        "-- ScholarFlow Big Mock Data (Robust Version)",
        "-- 这段 SQL 会自动将数据关联到你当前已有的账号上",
        "DO $$",
        "DECLARE",
        "  real_user_id UUID;",
        "BEGIN",
        "  -- 获取当前系统中的第一个真实用户（你自己）",
        "  SELECT id INTO real_user_id FROM auth.users LIMIT 1;",
        "",
        "  IF real_user_id IS NULL THEN",
        "    RAISE NOTICE 'No real users found. Please register an account first.';",
        "    RETURN;",
        "  END IF;",
        " "
    ]

    # --- 1. 生成虚拟审稿人的 Profile (不强制关联 auth.users) ---
    sql_output.append("  -- 1. 生成虚拟用户 Profile (这些用户仅存在于应用层，用于展示)")
    for i in range(20):
        uid = str(uuid.uuid4())
        full_name = f"Mock Reviewer {i+1}"
        email = f"reviewer{i+1}@mock.com"
        sql_output.append(
            f"  INSERT INTO public.user_profiles (id, email, full_name, roles)"
            f"  VALUES ('{uid}', '{email}', '{full_name}', ARRAY['reviewer']) ON CONFLICT DO NOTHING;"
        )

    # --- 2. 生成大量通知并关联到你的 ID ---
    sql_output.append("\n  -- 2. 为你的账号生成 100 条历史通知")
    types = ['submission', 'review_invite', 'decision', 'system']
    for i in range(100):
        ntype = random.choice(types)
        sql_output.append(
            f"  INSERT INTO public.notifications (user_id, type, title, content, is_read, created_at)"
            f"  VALUES (real_user_id, '{ntype}', 'Mock Notification {i+1}', 'This is a large scale test notification.', {str(random.choice([True, False])).lower()}, NOW() - INTERVAL '{i} hours');"
        )

    # --- 3. 生成大量稿件并关联到你的 ID ---
    sql_output.append("\n  -- 3. 为你的账号生成 50 篇稿件（你是作者或编辑）")
    status_list = ['submitted', 'under_review', 'accepted', 'published']
    for i in range(50):
        mid = str(uuid.uuid4())
        status = random.choice(status_list)
        sql_output.append(
            f"  INSERT INTO public.manuscripts (id, author_id, title, abstract, status, created_at)"
            f"  VALUES ('{mid}', real_user_id, 'Large Scale Test Paper {i+1}', 'Abstract for paper {i+1}...', '{status}', NOW() - INTERVAL '{i} days');"
        )

    sql_output.append("END $$")
    return "\n".join(sql_output)

if __name__ == "__main__":
    with open("big_mock_seed_v2.sql", "w") as f:
        f.write(generate_sql())
    print("Done! Generated big_mock_seed_v2.sql")