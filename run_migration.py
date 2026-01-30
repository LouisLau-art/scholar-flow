import psycopg2
import os

# 配置
DB_HOST = "db.mmvulyrfsorqdpdrzbkd.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "LiuXinyu200161"
DB_PORT = "5432"

def run_migrations():
    print("🚀 Connecting to Supabase Database...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. 读取基础 Schema
        print("📄 Reading schema.sql...")
        with open("backend/app/core/schema.sql", "r") as f:
            schema_sql = f.read()
            
        # 2. 读取查重 Schema
        print("📄 Reading plagiarism schema...")
        with open("supabase/migrations/20260127045433_add_plagiarism_reports.sql", "r") as f:
            plagiarism_sql = f.read()
            
        # 3. 读取 Mock 数据
        print("📄 Reading seed data...")
        with open("supabase/migrations/20260127044024_seed_reviewers.sql", "r") as f:
            seed_sql = f.read()

        # 执行
        print("⚡ Executing migrations...")
        cur.execute(schema_sql)
        cur.execute(plagiarism_sql)
        try:
            cur.execute(seed_sql)
        except Exception as e:
            print(f"⚠️ Seed data warning (might already exist): {e}")

        print("✅ Database migration completed successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    run_migrations()
