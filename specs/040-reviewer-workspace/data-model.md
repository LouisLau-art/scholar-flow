# Data Model & Contracts

**Feature**: Reviewer Workspace (Feature 040)
**Date**: 2026-02-06

## Data Model

### `review_reports` (Existing)
Updates to support the workspace fields.
- `comments_for_author` (Text, existing)
- `confidential_comments_to_editor` (Text, existing)
- `recommendation` (Enum, existing: `accept`, `minor_revision`, `major_revision`, `reject`)
- `attachment_paths` (JSONB or Array): New/Existing field to store paths to uploaded files in `review-attachments` bucket.

### `review_assignments` (Existing)
- `status`: Transition `accepted` -> `completed` (or `submitted`).

## API Contracts

### 1. Get Workspace Data (Reviewer)

**Endpoint**: `GET /api/v1/reviewer/assignments/{assignment_id}/workspace`
**Access**: Reviewer (Guest or Auth) - Must match assignment.

**Response**:
```json
{
  "manuscript": {
    "id": "uuid",
    "title": "...",
    "abstract": "...",
    "pdf_url": "signed_url_valid_for_1h"
  },
  "review_report": {
    "id": "uuid",
    "status": "pending",
    "comments_for_author": "Draft...",
    "confidential_comments_to_editor": "Draft...",
    "recommendation": null,
    "attachments": []
  },
  "permissions": {
    "can_submit": true,
    "is_read_only": false
  }
}
```

### 2. Save Draft (Auto-save or Manual)

**Endpoint**: `PUT /api/v1/reviewer/assignments/{assignment_id}/draft`
**Access**: Reviewer.

**Request**:
```json
{
  "comments_for_author": "...",
  "confidential_comments_to_editor": "...",
  "recommendation": "minor_revision",
  "attachments": ["path/to/file.pdf"]
}
```

### 3. Submit Review

**Endpoint**: `POST /api/v1/reviewer/assignments/{assignment_id}/submit`
**Access**: Reviewer.

**Request**:
```json
{
  "comments_for_author": "...",
  "confidential_comments_to_editor": "...",
  "recommendation": "accept",
  "attachments": ["path/to/file.pdf"]
}
```

**Response**:
```json
{
  "success": true,
  "status": "completed",
  "redirect_to": "/review/thank-you"
}
```

### 4. Upload Attachment

**Endpoint**: `POST /api/v1/reviewer/assignments/{assignment_id}/attachments`
**Type**: Multipart/Form-Data.
**Response**: `{"path": "assignments/123/notes.pdf", "url": "..."}`
