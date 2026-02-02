# Specification: User Profile & Security Center

## 1. Overview
The User Profile & Security Center is a centralized self-management interface for all authenticated users (Authors, Editors, Reviewers). It enables users to maintain their personal information, academic credentials, and account security settings. This feature ensures data consistency across the application, enhances the accuracy of the AI reviewer matching system (Feature 012) via research interests, and provides a secure mechanism for password updates and avatar management.

## Clarifications
### Session 2026-01-31
- Q: Avatar Constraints (Size/Format)? → A: Strict Limits: Max 2MB size; JPG, PNG, WEBP formats only.
- Q: Research Interest Limits? → A: Max 10 tags per user, max 50 characters per tag.
- Q: Conflict Resolution Strategy? → A: Last Write Wins (standard single-user profile updates).
- Q: Old Password Requirement? → A: Skip for MVP (allow password update via session auth only).
- Q: User Interface Tab Structure? → A: Three tabs: Profile (Basic Info + Avatar), Academic (Interests + ORCID/Scholar), and Security (Password).

## 2. User Scenarios

### 2.1 Profile Management
- **Actor**: Any Authenticated User (Author, Editor, Reviewer)
- **Preconditions**: User is logged in.
- **Trigger**: User clicks their avatar in the navigation bar and selects "Settings" or "Profile" from the dropdown.
- **Flow**:
  1. User navigates to the profile settings page (defaulting to the **Profile** tab).
  2. User edits their "Full Name", "Title" (e.g., Dr./Prof.), or "Affiliation".
  3. User switches to the **Academic** tab to add or remove "Research Interests" using a tag input system.
  4. User clicks "Save".
  5. System validates inputs (respecting tag limits) and updates the profile data.
  6. UI updates immediately (e.g., navbar name reflects changes).
- **Postconditions**: User profile is updated in the database; "Research Interests" are available for AI matching.

### 2.2 Avatar Upload
- **Actor**: Any Authenticated User
- **Flow**:
  1. User clicks the avatar upload area in the **Profile** settings.
  2. User selects an image file.
  3. System validates the file type (JPG/PNG/WEBP) and size (Max 2MB).
  4. System uploads the image to the secure storage provider.
  5. System updates the user's profile with the new avatar URL.
  6. The new avatar is displayed immediately in the interface.

### 2.3 Security - Change Password
- **Actor**: Any Authenticated User
- **Flow**:
  1. User switches to the **Security** tab.
  2. User enters a new password and confirms it (old password not required for MVP).
  3. User clicks "Update Password".
  4. System updates the credentials via the authentication provider.
  5. System displays a success notification.
- **Alternative Flow (Failure)**:
  1. Password update fails (e.g., weak password).
  2. System displays a clear error message explaining the failure.

## 3. Functional Requirements

### 3.1 Profile Information
- **FR-01**: The system MUST provide a form to edit the following fields:
  - Full Name (Text, Required)
  - Title (Text/Select, Optional)
  - Affiliation (Text, Required)
  - ORCID ID (Text, Optional, Validation for format)
  - Google Scholar Link (URL, Optional, Validation for URL format)
- **FR-02**: The system MUST provide a "Research Interests" field allowing users to add and remove text tags.
  - Limit: Max 10 tags per user.
  - Limit: Max 50 characters per tag.
- **FR-03**: The system MUST synchronize research interest tags with the user's profile data to support downstream AI matching.

### 3.2 Avatar Management
- **FR-04**: The system MUST allow users to upload an image file to serve as their profile avatar.
- **FR-05**: The system MUST enforce access control on avatar files:
  - Users can only upload/overwrite their own avatar.
  - Avatar files must be readable by all users (or authenticated users).
- **FR-06**: The system MUST display a friendly error message if the image upload fails (e.g., file too large, network error).
- **FR-13**: The system MUST enforce strict validation on avatar uploads:
  - Allowed Formats: JPG, PNG, WEBP.
  - Max File Size: 2MB.

### 3.3 Security Settings
- **FR-07**: The system MUST provide a "Change Password" interface requiring "New Password" and "Confirm New Password".
- **FR-08**: The system MUST verify that the new password and confirmation match before processing.
- **FR-09**: The system MUST securely update the user's authentication credentials via the session-based API.
- **FR-10**: The system MUST provide immediate visual feedback (Success/Error) upon completion of the password update request.

### 3.4 Data & UI Consistency
- **FR-11**: Updates to user profile information (Name, Avatar) MUST be immediately reflected in the global navigation and context without requiring a page reload.
- **FR-12**: The user interface MUST maintain visual and interactive consistency with the core dashboard application using a three-tab layout.

## 4. Non-Functional Requirements

### 4.1 Security & Permissions
- **NFR-01 (Access Control)**: The system MUST strictly enforce Row Level Security (or equivalent) to ensure users can ONLY update their own profile records.
- **NFR-02 (Storage Security)**: Storage policies MUST prevent unauthorized deletion or modification of other users' avatar files.

### 4.2 Usability
- **NFR-03**: Form validation errors MUST be displayed inline or via a toast notification.
- **NFR-04**: The Research Interest tag input MUST support standard keyboard interactions (Enter to add, Backspace to delete).

### 4.3 Performance
- **NFR-05**: Profile updates MUST be processed and reflected in the UI within 1 second under normal network conditions.

## 5. Data Entities & Schema

### 5.1 Profiles Table
- **Entity**: `User Profile`
- **Fields**:
  - `full_name`: String
  - `avatar_url`: String (URL)
  - `affiliation`: String
  - `title`: String
  - `orcid_id`: String
  - `google_scholar_url`: String (URL)
  - `research_interests`: List<String> (Stored as Array or Vector)

### 5.2 Storage
- **Container**: `avatars`
- **Structure**: User-segregated paths (e.g., `avatars/{user_id}/...`).

## 6. Success Criteria
- **SC-01**: User can update their "Full Name" and see the change immediately in the application header.
- **SC-02**: User can successfully upload a valid image file (JPG/PNG/WEBP, <2MB) and see it replace their current avatar.
- **SC-03**: User can save up to 10 "Research Interests" tags, which persist after reloading the page.
- **SC-04**: User cannot modify the profile data of another user (verified via security tests).
- **SC-05**: User can change their password and successfully log in with the new credentials.

## 7. Technical Constraints
- **TC-01**: Password updates MUST use the `supabase.auth.updateUser` API method.
- **TC-02**: The UI MUST be implemented using Shadcn/UI components (`Tabs`, `Form`, `Input`, `Avatar`) to match the project's design system.
- **TC-03**: Avatars MUST be stored in the Supabase Storage `avatars` bucket.
- **TC-04**: Research interests MUST be stored in a format compatible with the `pgvector` extension usage in Feature 012.

## 8. Assumptions
- Feature 012 (AI Matchmaker) will handle the actual vectorization of `research_interests` if necessary.
- Email change functionality is out of scope for this MVP iteration.
- Concurrent edit conflicts will be handled via "Last Write Wins".
