# Research: User Acceptance Testing (UAT) & Staging Environment Setup

## 1. Environment Isolation Strategy

**Decision:** Use `NEXT_PUBLIC_APP_ENV` with conditional rendering and `next/dynamic` for code splitting.

**Rationale:**
Next.js 14's App Router uses SWC for compilation. Prefixing environment variables with `NEXT_PUBLIC_` ensures they are inlined at build time.
- If `process.env.NEXT_PUBLIC_APP_ENV === 'staging'` evaluates to false (e.g., in Production), minifiers like Terser/SWC will identify the code inside the conditional block as dead code and strip it from the client bundle.
- Using `next/dynamic` for the Feedback Widget ensures that even if some references remain, the heavy UI code (Shadcn dialog, form logic) is split into a separate chunk that is never loaded by the browser in Production.

**Implementation:**
```typescript
// src/lib/env.ts
export const APP_ENV = process.env.NEXT_PUBLIC_APP_ENV || 'development';
export const IS_STAGING = APP_ENV === 'staging';

// src/components/providers/EnvironmentProvider.tsx
if (IS_STAGING) {
  // Render Banner & Widget
}
```

## 2. Supabase Staging Strategy

**Decision:** Use a **Separate Supabase Project** for Staging.

**Rationale:**
- **Data Safety:** "Schema isolation" (e.g., using a `staging` schema in the same DB) is risky because PostgREST (Supabase's API layer) exposes the `public` schema by default. configuring it to switch schemas based on headers is complex and error-prone. One mistake could wipe production data.
- **Parity:** A separate project ensures exact parity in configuration (Auth settings, Storage buckets, Edge Functions) which might drift if managed manually in a shared instance.
- **Workflow:** Allows "nuke and pave" (complete reset) of the Staging DB without any risk to Production uptime or data integrity.

## 3. Feedback Widget Implementation

**Decision:** Build a custom **Shadcn UI** component within the frontend codebase.

**Rationale:**
- **Lightweight:** Avoiding third-party widgets (like Sentry Replay or UserVoice) keeps the bundle size small and prevents tracking script blockers from hiding the widget.
- **Integration:** Since we use Shadcn UI, the look and feel will be consistent.
- **Context:** We can easily capture application state (Redux/Context, URL, User ID) and send it directly to our own backend, keeping data ownership internal.

**API Contract:**
`POST /api/v1/system/feedback`
Payload: `{ description: string, severity: string, url: string, user_id?: string }`

## 4. Data Seeding Strategy

**Decision:** Python Script (`backend/scripts/seed_staging.py`) using `supabase-py`.

**Rationale:**
- **Auth Handling:** Standard SQL seed files cannot easily create Supabase Auth users (due to password hashing and internal `auth` schema protections). The Supabase Admin API (via Python client) allows creating users with specific passwords, which is essential for "Demo Accounts".
- **Relational Integrity:** A script can create a user, get their ID, and immediately use it to create related records (Manuscripts, Profiles) with correct foreign keys, which is hard to coordinate in static SQL.
- **Automation:** Can be triggered via CI/CD or manually by admins.

**Script Flow:**
1. Connect to Staging DB (Service Role Key).
2. `rpc("truncate_all_tables")` (Custom function to clean DB).
3. `auth.admin.create_user()` (Create Editor, Reviewer, Author).
4. `table("manuscripts").insert()` (Create specific scenarios).
