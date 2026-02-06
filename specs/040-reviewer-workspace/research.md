# Research: Reviewer Workspace Tech Stack

**Feature**: Reviewer Workspace (Feature 040)
**Date**: 2026-02-06

## 1. PDF Rendering Strategy

### Decision
Use **Native `<iframe>`** initially, fallback/upgrade to `react-pdf` if annotation needed later.

### Rationale
- **Simplicity**: Most modern browsers render PDFs natively with high performance and built-in controls (zoom, scroll).
- **Glue Coding**: Avoids adding heavy dependencies (`react-pdf` + worker) for simple viewing.
- **Mobile**: Native viewers often handle mobile touch gestures better than JS implementations.

### Implementation Details
- URL: Backend generates a signed URL (short expiry) -> Frontend sets `src`.
- Permissions: Add `sandbox` attributes to iframe if needed for security (though PDF is static).

## 2. Form State Management & "Warn on Exit"

### Decision
Use **React Hook Form** + `useBeforeUnload` (custom hook).

### Rationale
- **Performance**: Uncontrolled inputs reduce re-renders compared to strict controlled state.
- **Dirty Tracking**: `formState.isDirty` provides immediate "unsaved changes" status.
- **Pattern**: Existing project standard (assumed/recommended).

### Implementation
- `useForm({ defaultValues: fetchedData })`
- `useEffect` listening to `isDirty`: if dirty, add `window.addEventListener('beforeunload', ...)`

## 3. Layout Architecture

### Decision
**Route Group `(reviewer)`** with a dedicated `layout.tsx`.

### Rationale
- **Isolation**: Completely separates the review interface from the main dashboard (`(dashboard)` or similar).
- **Control**: Allows stripping out the Sidebar, Header, and Footer at the root level for this section.
- **Security**: Can apply a layout-level check (though Middleware handles the route, Layout handles the UI shell).

## 4. Attachment Storage

### Decision
Use existing `review-attachments` bucket (from Feature 033).

### Rationale
- **Reuse**: Feature 033 already established the bucket and schema (`public.manuscript_files`).
- **Path**: `assignments/{assignment_id}/{filename}` allows easy cleanup and scoped access.

## 5. Mobile Responsiveness

### Decision
**CSS Grid / Flex with Media Query Toggle**.

### Pattern
- **Desktop**: `grid-cols-2` (Left: PDF 50%, Right: Form 50% or resizable).
- **Mobile**: `flex-col`.
  - Default: Form visible.
  - Action: "View Manuscript" button overlays the PDF viewer (modal or full screen toggle).
- **Reason**: Side-by-side is impossible on phones. Prioritize the *Action* (Form) but allow reference (PDF).
