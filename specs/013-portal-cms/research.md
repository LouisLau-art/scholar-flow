# Research: Dynamic Portal CMS

**Feature Branch**: `013-portal-cms`
**Date**: 2026-01-30
**Input**: Feature spec.md and implementation plan.

## 1. Rich Text Editor Selection

- **Options**: Tiptap, React-Quill, Slate.js.
- **Decision**: **Tiptap**.
- **Rationale**: 
  - Headless architecture fits perfectly with Shadcn/UI (full styling control).
  - Modern, actively maintained, and excellent TypeScript support.
  - React-Quill is older and harder to style custom classes (Tailwind).
  - Slate.js is too low-level/complex for this simple requirement.
- **Implementation**: Install `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-image`.

## 2. HTML Sanitization

- **Decision**: **Backend (Bleach)** + **Frontend (DOMPurify)**.
- **Rationale**: 
  - **Defense in Depth**: Sanitize on write (Backend) to protect the DB and other consumers. Sanitize on read (Frontend) as a failsafe before `dangerouslySetInnerHTML`.
  - **Backend**: Python `bleach` is standard.
  - **Frontend**: `isomorphic-dompurify` for Next.js (SSR compatible).

## 3. ISR Strategy (Next.js)

- **Decision**: `revalidate: 60` (1 minute).
- **Rationale**: 
  - CMS content changes infrequently.
  - 60 seconds is a good balance between "instant updates" and "cache efficiency".
  - On-demand revalidation (via API webhook) is cleaner but more complex to setup. Time-based ISR is sufficient for MVP.

## 4. Image Upload Flow

- **Decision**: Direct Upload to Supabase via Signed URL (Frontend) or Proxy via Backend?
- **Decision**: **Proxy via Backend API**.
- **Rationale**: 
  - Keeps Auth logic centralized.
  - Editor uploads to `POST /api/v1/cms/upload`.
  - Backend validates file type/size, uploads to Supabase Storage, returns Public URL.
  - Tiptap inserts the URL.
  - Avoiding direct client-side upload prevents leaking Supabase anon keys or dealing with complex RLS for "write-only" buckets.

## 5. DB Schema Details

- **Slug Uniqueness**:
  - Must enforce `UNIQUE` constraint on `cms_pages(slug)`.
  - Reserved slugs list: `admin`, `login`, `register`, `submit`, `api`.
