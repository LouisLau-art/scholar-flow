# Data Model

**Feature**: Core Logic Hardening
**Source**: Supabase (PostgreSQL)

## Schema Updates

### 1. Table: `review_reports`

**Purpose**: Store peer review content.
**Change**: Add confidential fields.

| Column Name | Type | Nullable | Description |
|-------------|------|----------|-------------|
| `confidential_comments_to_editor` | `TEXT` | Yes | Private comments visible only to editors. |
| `attachment_path` | `TEXT` | Yes | Path to confidential reviewer attachment in storage. |

**SQL Migration**:
```sql
ALTER TABLE public.review_reports 
ADD COLUMN IF NOT EXISTS confidential_comments_to_editor TEXT,
ADD COLUMN IF NOT EXISTS attachment_path TEXT;
```

### 2. Table: `invoices`

**Purpose**: Track payment status for manuscripts.
**Change**: Ensure existence and structure (already verified in research, but documenting usage).

| Column Name | Type | Nullable | Description |
|-------------|------|----------|-------------|
| `manuscript_id` | `UUID` | No | Foreign Key to Manuscripts. |
| `amount` | `NUMERIC` | No | APC amount. |
| `status` | `TEXT` | No | 'unpaid', 'paid', 'waived'. Default 'unpaid'. |

## Security Policies (RLS)

- **review_reports**:
  - `SELECT`:
    - **Reviewer**: Can see own reports.
    - **Editor/Admin**: Can see all fields.
    - **Author**: Can see `comments` (public), but **NEVER** `confidential_comments_to_editor` or `attachment_path`. (Enforced by API, but RLS column security would be better if supported easily, otherwise API filtering). *Note: Supabase/Postgres RLS is row-level. Column-level security is tricky. We will rely on API Layer filtering for "Privacy Window Control" as specified.*

- **invoices**:
  - `SELECT`: Visible to Editor/Admin/Author (own).
  - `UPDATE`: Editor/Admin only (for amount). System (webhook) for status.
