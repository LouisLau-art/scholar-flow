# Research & Decisions: User Profile System

## 1. Data Flow Architecture
**Decision**: Hybrid Approach.
- **Profile Data (Text)**: Route through Backend API (`PUT /api/v1/user/profile`).
  - **Rationale**:
    1.  Allows centralized validation (Pydantic).
    2.  Enables triggering downstream side-effects (e.g., re-indexing Research Interests for AI matching) reliably in the backend.
    3.  Keeps frontend thin and consistent with other modules (Manuscripts, Reviews).
- **Avatar Upload**: Direct to Supabase Storage from Frontend.
  - **Rationale**:
    1.  Avoids burdening the Python backend with binary file transfer.
    2.  Utilizes Supabase's native CDN/Storage capabilities efficiently.
    3.  The returned URL is then sent to the Backend API during the profile update (or a separate patch).
- **Password Change**: Route through Backend API (`PUT /api/v1/user/security/password`).
  - **Rationale**:
    1.  Standardizes logging (Audit Logs).
    2.  Abstracts the Auth provider implementation details.

## 2. Storage Strategy
**Decision**: User-Segregated Paths.
- **Path**: `avatars/{user_id}/avatar.{ext}`
- **Policy**:
  - `INSERT`: `auth.uid() = name[0]` (users can only write to their folder).
  - `SELECT`: `public` (anyone can see avatars).
  - `UPDATE`: `auth.uid() = name[0]`.
- **Constraint**: File size < 2MB, Type in [jpg, png, webp].

## 3. UI/UX Pattern
**Decision**: 3-Tab "Settings" Page.
- **Components**: Shadcn `Tabs`, `Card`, `Form`.
- **State Management**: React Query (TanStack Query) for fetching/updating profile data to ensure instant cache invalidation and UI updates (NFR-05).
