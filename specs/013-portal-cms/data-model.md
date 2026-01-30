# Data Model: Dynamic Portal CMS

**Feature Branch**: `013-portal-cms`
**Date**: 2026-01-30

**Migration**: `supabase/migrations/20260130193000_add_portal_cms.sql`

## Entities

### 1. CMS Page
**Table**: `public.cms_pages`

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| id | uuid | PK, Default: gen_random_uuid() | Unique ID |
| slug | text | UNIQUE, NOT NULL | URL path segment (e.g. "about") |
| title | text | NOT NULL | Page H1 title |
| content | text | | Sanitized HTML content |
| is_published | boolean | Default: false | Visibility flag |
| created_at | timestamptz | Default: now() | |
| updated_at | timestamptz | Default: now() | |
| updated_by | uuid | FK -> auth.users | Audit trail |

**RLS Policies**:
- `SELECT`: Public (if `is_published=true`), Editor (all).
- `INSERT/UPDATE/DELETE`: Editor role only.

### 2. CMS Menu Item
**Table**: `public.cms_menu_items`

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| id | uuid | PK, Default: gen_random_uuid() | Unique ID |
| parent_id | uuid | FK -> cms_menu_items(id), Nullable | For dropdown sub-menus |
| label | text | NOT NULL | Display text |
| url | text | | External URL or path |
| page_id | uuid | FK -> cms_pages(id), Nullable | Link to internal CMS page |
| order_index | integer | Default: 0 | Sort order |
| location | text | Check ('header', 'footer') | Where this item appears |

**RLS Policies**:
- `SELECT`: Public (all).
- `INSERT/UPDATE/DELETE`: Editor role only.

## Validation Rules
- `slug`: Regex `^[a-z0-9-]+$`.
- `page_id` vs `url`: **不能同时设置**；允许两者都为空（用于“分组标题/下拉父级”）。
- `order_index`: Unique per parent scope (preferred, but soft constraint ok).

## State Transitions
- **Draft -> Published**: Page becomes visible to public RLS policy.
- **Published -> Draft**: Page disappears from public view (404).
