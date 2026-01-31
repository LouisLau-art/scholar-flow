# Tasks: User Profile & Security Center

## Phase 1: Setup & Infrastructure
- [x] T001 Create database migration for `profiles` table updates (add `research_interests`, `orcid_id`, etc.) in `supabase/migrations/`
- [x] T002 Create SQL script for `avatars` storage bucket and RLS policies in `supabase/migrations/` (or execute in dashboard and save SQL)
- [x] T003 [P] Update backend Pydantic models for `UserProfile` schema in `backend/app/schemas/user.py`
- [x] T004 [P] Update backend database models (SQLModel/SQLAlchemy) in `backend/app/models/user.py`

## Phase 2: Foundational (Backend Services)
- [x] T005 [P] Implement `UserService.update_profile` logic in `backend/app/services/user_service.py`
- [x] T006 [P] Implement `UserService.change_password` logic in `backend/app/services/user_service.py` (wrapping Supabase Admin API)
- [x] T007 Create API endpoint `PUT /api/v1/user/profile` in `backend/app/api/v1/user.py`
- [x] T008 Create API endpoint `PUT /api/v1/user/security/password` in `backend/app/api/v1/user.py`
- [x] T009 [P] Add backend integration tests for profile and password endpoints in `backend/tests/integration/test_user_profile.py`

## Phase 3: User Story 1 - Profile Management
- [x] T010 [US1] Create `ProfilePage` layout with Tabs (Profile, Academic, Security) in `frontend/src/app/settings/page.tsx`
- [x] T011 [US1] Implement `ProfileForm` component (Basic Info) in `frontend/src/components/settings/ProfileForm.tsx`
- [x] T012 [P] [US1] Implement `TagInput` component for Research Interests in `frontend/src/components/ui/TagInput.tsx`
- [x] T013 [US1] Integrate `ResearchInterests` section into `ProfileForm` in `frontend/src/components/settings/ProfileForm.tsx`
- [x] T014 [US1] Wire up `ProfileForm` to `PUT /api/v1/user/profile` using React Query in `frontend/src/hooks/useProfile.ts`
- [x] T015 [US1] Ensure global Navbar updates name immediately upon save in `frontend/src/components/layout/Navbar.tsx` (via context/query invalidation)

## Phase 4: User Story 2 - Avatar Upload
- [x] T016 [US2] Implement `AvatarUpload` component with file validation (Size/Type) in `frontend/src/components/settings/AvatarUpload.tsx`
- [x] T017 [US2] Implement direct-to-Supabase storage upload logic in `frontend/src/services/storage.ts`
- [x] T018 [US2] Integrate `AvatarUpload` into `ProfilePage` and handle URL update in `frontend/src/app/settings/page.tsx`

## Phase 5: User Story 3 - Security (Password)
- [x] T019 [P] [US3] Implement `PasswordChangeForm` component with validation (match check) in `frontend/src/components/settings/PasswordChangeForm.tsx`
- [x] T020 [US3] Wire up `PasswordChangeForm` to `PUT /api/v1/user/security/password` in `frontend/src/components/settings/PasswordChangeForm.tsx`

## Phase 6: Polish & Cross-Cutting
- [x] T021 [P] Add error handling and Toast notifications for all forms in `frontend/src/app/settings/page.tsx`
- [x] T022 [P] Verify RLS: Ensure user cannot update another user's profile (Manual verify or Test)
- [x] T023 Run full regression test suite

## Dependencies
- Phase 2 depends on Phase 1
- Phase 3, 4, 5 depend on Phase 2 (Backend APIs ready)
- T015 depends on T014

## Implementation Strategy
- **MVP**: Focus on Phase 1 & 2 first to get the data layer ready. Then build the frontend tabs one by one.
- **Parallelism**: Backend and Frontend tasks can run in parallel once the API contract (T003, T007) is agreed upon. TagInput (T012) can be built independently.