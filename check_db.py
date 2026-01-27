import psycopg2
import sys

# 配置
DB_HOST = "db.mmvulyrfsorqdpdrzbkd.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "LiuXinyu200161"
DB_PORT = "5432"

try:
    print(f"🔄 正在尝试连接 {DB_HOST}:{DB_PORT} ...")
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        connect_timeout=5  # 5秒超时
    )
    print("✅ 连接成功！当前环境可以直连 Supabase 数据库。")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"❌ 连接失败: {str(e)}")
    print("⚠️ 原因可能是当前网络环境封锁了 5432 端口出口，或者 Supabase 开启了 IP 白名单。")
    sys.exit(1)
