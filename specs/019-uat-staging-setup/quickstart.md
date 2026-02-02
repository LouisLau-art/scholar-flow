# Quickstart: UAT & Staging Setup

## Prerequisites

- Python 3.10+ and pip
- Node.js 20+ and npm
- Supabase Project (Create a new project for Staging if testing isolation locally)

## 1. Environment Configuration

### Frontend (.env.local)
```bash
# Enable Staging Mode
NEXT_PUBLIC_APP_ENV="staging"
```

### Backend (.env)
```bash
# Point to Staging Database (or local test instance)
SUPABASE_URL="https://your-staging-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

## 2. Running the Seed Script

To wipe the staging database and populate it with demo scenarios:

```bash
cd backend
# Ensure virtualenv is active
source .venv/bin/activate

# Run the seed script
python -m scripts.seed_staging
```

**Expected Output:**
```text
⚠️  Wiping Staging Data...
Creating test users...
Seeding manuscripts...
✅  Staging environment reset successfully.
```

## 3. Verifying the Setup

1. **Start Frontend**: `npm run dev`
2. **Check Banner**: Open `http://localhost:3000`. You should see the yellow "UAT Staging" banner at the bottom.
3. **Check Widget**: Click the "Bug" icon in the bottom right corner.
4. **Submit Feedback**: Fill the form and submit.
5. **Verify Data**: Check the `uat_feedback` table in your Staging Supabase dashboard.

## 4. Troubleshooting

- **Banner not showing?** Ensure `NEXT_PUBLIC_APP_ENV` is exactly "staging" and you restarted the dev server.
- **Seed script fails?** Ensure you are using the `SERVICE_ROLE_KEY` (not Anon key) as it requires admin privileges to manage Auth users.
