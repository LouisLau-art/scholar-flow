# Quickstart: Notification Center

## Prerequisites

1. **Environment Variables**:
   Ensure `.env` (backend) contains SMTP settings:
   ```bash
   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USER=your_user
   SMTP_PASSWORD=your_password
   SMTP_FROM_EMAIL=no-reply@your-journal.org
   ADMIN_API_KEY=your_secret_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   FRONTEND_BASE_URL=http://localhost:3000
   ```

2. **Database Migration**:
   Run the migration to create `notifications` table and add `last_reminded_at`.

## Verification Steps

### 1. In-App Notification (Realtime)
1. Open the frontend app and login as **Editor**.
2. Open a second browser/tab, login as **Author**.
3. As Author, submit a new manuscript.
4. Watch the Editor's screen: The **Bell Icon** should immediately show a red dot.
5. Click the Bell: You should see "New Submission: {Title}".

### 2. Email Delivery (Mock/Real)
1. Check the backend logs or your email inbox (if SMTP configured).
2. Look for "Sending email to {author_email}... Success".

### 3. Auto-Chasing (Manual Trigger)
1. Use `curl` or Postman to trigger the cron endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/internal/cron/chase-reviews \
     -H "X-Admin-Key: your_secret_key"
   ```
2. Verify response: `{"processed_count": X, "emails_sent": Y}`.
