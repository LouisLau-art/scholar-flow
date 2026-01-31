import os
import sys
from supabase import create_client, Client

# Use Service Role Key to bypass RLS and manage Auth
url = os.environ.get("SUPABASE_URL")
# For seeding, we MUST use the service role key to wipe data and create auth users
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print(
        "❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables."
    )
    sys.exit(1)

supabase: Client = create_client(url, key)


def reset_and_seed():
    print("⚠️  Wiping Staging Data...")
    try:
        # 1. Clean Slate: Call stored procedure to truncate tables with CASCADE
        # Ensure rpc_truncate_all_tables migration has been applied
        response = supabase.rpc("truncate_all_tables", {}).execute()
        print("   Tables truncated.")
    except Exception as e:
        print(f"❌ Error truncating tables: {e}")
        # Continue? No, unsafe to seed on dirty DB
        sys.exit(1)

    # 2. Seed Auth Users
    users = {}
    print("Creating test users...")
    try:
        # Create Editor
        editor = supabase.auth.admin.create_user(
            {
                "email": "editor@scholarflow.test",
                "password": "password123",
                "email_confirm": True,
                "user_metadata": {"full_name": "Staging Editor", "roles": ["editor"]},
            }
        )
        users["editor"] = editor.user.id
        print(f"   Created Editor: {editor.user.id}")

        # Create Reviewer (for overdue task)
        reviewer = supabase.auth.admin.create_user(
            {
                "email": "reviewer@scholarflow.test",
                "password": "password123",
                "email_confirm": True,
                "user_metadata": {
                    "full_name": "Overdue Reviewer",
                    "roles": ["reviewer"],
                },
            }
        )
        users["reviewer"] = reviewer.user.id
        print(f"   Created Reviewer: {reviewer.user.id}")

        # Create Author
        author = supabase.auth.admin.create_user(
            {
                "email": "author@scholarflow.test",
                "password": "password123",
                "email_confirm": True,
                "user_metadata": {"full_name": "Test Author", "roles": ["author"]},
            }
        )
        users["author"] = author.user.id
        print(f"   Created Author: {author.user.id}")

    except Exception as e:
        print(f"❌ Error creating users: {e}")
        print("   (Users might already exist, continuing...)")
        # In robust script, fetch existing users by email
        sys.exit(1)

    # 3. Seed Business Data
    print("Seeding manuscripts...")

    # Scenario A: Pending Manuscript (Biology)
    supabase.table("manuscripts").insert(
        {
            "title": "Impact of Climate Change on Arctic Flora",
            "abstract": "A comprehensive study of plant resilience in warming climates...",
            "submitter_id": users["author"],
            "status": "submitted",
            "field": "Biology",
        }
    ).execute()

    # Scenario B: Overdue Review (Chemistry) - Assigned to Reviewer
    ms_chem = (
        supabase.table("manuscripts")
        .insert(
            {
                "title": "Novel Catalysts for Carbon Capture",
                "abstract": "Synthesizing efficient MOFs for industrial applications...",
                "submitter_id": users["author"],
                "status": "under_review",
                "field": "Chemistry",
            }
        )
        .execute()
        .data[0]
    )

    # Create overdue assignment (due date in past)
    supabase.table("review_assignments").insert(
        {
            "manuscript_id": ms_chem["id"],
            "reviewer_id": users["reviewer"],
            "status": "pending",
            "due_date": "2023-01-01T00:00:00Z",  # Way overdue
        }
    ).execute()

    # Scenario C: Unpaid Acceptance (Physics)
    supabase.table("manuscripts").insert(
        {
            "title": "Quantum Entanglement at Macroscopic Scales",
            "abstract": "Experimental verification of bell inequalities...",
            "submitter_id": users["author"],
            "status": "accepted",
            "field": "Physics",
            # Assuming we have an apc_status column or similar logic
            # "apc_status": "pending_payment"
        }
    ).execute()

    print("✅  Staging environment reset successfully.")


if __name__ == "__main__":
    reset_and_seed()
