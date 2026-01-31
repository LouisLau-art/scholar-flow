# Implementation Plan - User Profile & Security Center

## Technical Context

### 1. Existing System
- **Frontend**: Next.js 14.2 (App Router), React 18, Tailwind CSS, Shadcn/UI.
- **Backend**: FastAPI 0.115+, Pydantic v2.
- **Database**: Supabase (PostgreSQL), `public.profiles` table linked to `auth.users`.
- **Storage**: Supabase Storage (`avatars` bucket).
- **Auth**: Supabase Auth (JWT).

### 2. Key Decisions (from Spec Clarifications)
- **Avatar Limits**: Max 2MB, JPG/PNG/WEBP.
- **Tag Limits**: Max 10 tags, 50 chars each.
- **Security**: Password update via `supabase.auth.updateUser` (no old password check for MVP).
- **UX**: Three-tab layout (Profile, Academic, Security).
- **Storage Policy**: Public read, Authenticated write (user-segregated).

### 3. Dependencies
- **Supabase JS Client**: `@supabase/supabase-js` (Frontend).
- **Supabase Python Client**: `supabase` (Backend, if needed for admin overrides, though spec implies direct frontend interaction for profile updates? Spec says "Backend calls Supabase Auth API" for password? No, spec says "Backend call... supabase.auth.updateUser". Wait, the spec text actually said: "Backend call... (`supabase.auth.updateUser`)". Usually `updateUser` is called from the client SDK for self-service. If called from backend, it uses `admin.updateUserById`.
- **Clarification**: The spec says "Backend call...". However, Feature 018 is "User Self Management". In Supabase architecture, users typically update their own password via the Frontend JS SDK (`supabase.auth.updateUser`). Using a backend proxy adds latency and complexity unless specific logging is needed.
- **Decision**: I will assume the standard Supabase pattern: **Frontend directly calls Supabase** for profile updates (RLS protected) and password updates (Auth API), unless the backend is required for specific validation or logging not possible in RLS. Given the "Backend call" note in the prompt, I will double-check if we *must* route through FastAPI. The prompt said "Backend call Supabase Auth API...". I will respect that if it implies a backend endpoint wrapper, possibly for audit logs. However, the `profiles` update is definitely RLS/Frontend. Let's look at the "Technical Constraints": "Password updates MUST use the `supabase.auth.updateUser` API method." This method exists in both JS Client and Admin API.
- **Refined Decision**: To maintain architectural consistency with previous features (like 017 Admin), I will route sensitive operations (Password) through the Backend API (`/api/v1/user/security/password`) to allow for **Audit Logging** and consistent error handling, even if Supabase allows direct calls. Profile data updates can remain direct or proxy. Given the "Data Consistency" requirement (NFR-05 < 1s), direct RLS is faster. But Feature 017 established a backend service pattern.
- **Hybrid Approach**:
    - **Profile Data**: Frontend -> Backend (`/api/v1/user/profile`) -> Database. (Ensures validation logic lives in one place and Feature 012 sync triggers can happen reliably).
    - **Password**: Frontend -> Backend (`/api/v1/user/security/password`) -> Supabase Admin API.
    - **Avatar**: Frontend -> Supabase Storage (Direct) -> Get URL -> Backend Update. (Direct upload prevents backend bottleneck for files).

## Constitution Check

### I. Library-First
- N/A (Feature is app-centric).

### II. CLI Interface
- N/A.

### III. Reproducibility
- All schema changes via SQL migrations.
- Storage policies via SQL.

## Gates
- [x] Spec is clear (Clarifications resolved).
- [x] Tech stack defined (Next.js + FastAPI + Supabase).
- [x] RLS/Storage policies defined.