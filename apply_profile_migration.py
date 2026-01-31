import psycopg2
import os

# Credentials from run_migration.py
DB_HOST = "db.mmvulyrfsorqdpdrzbkd.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "LiuXinyu200161"
DB_PORT = "5432"

MIGRATION_FILES = [
    "supabase/migrations/20260131120000_add_user_profile_fields.sql",
    "supabase/migrations/20260131120500_add_avatars_bucket.sql"
]

def apply_migrations():
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
        
        for file_path in MIGRATION_FILES:
            print(f"📄 Reading {file_path}...")
            try:
                with open(file_path, "r") as f:
                    sql = f.read()
                
                print(f"⚡ Executing {file_path}...")
                cur.execute(sql)
                print(f"✅ Executed {file_path}")
            except FileNotFoundError:
                print(f"❌ File not found: {file_path}")
            except Exception as e:
                print(f"❌ Error executing {file_path}: {e}")
                # We continue to next file even if one fails (e.g. if column exists)

        print("🎉 All profile migrations completed!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection/Migration failed: {e}")

if __name__ == "__main__":
    apply_migrations()
