# Implementation Plan: Refine Portal Home and Navigation

**Branch**: `034-portal-refinement` | **Date**: 2026-02-05 | **Spec**: [specs/034-portal-refinement/spec.md](spec.md)

## Summary
Upgrade the public-facing homepage and site-wide navigation to match professional academic standards. This includes a high-impact banner, a standardized academic footer, and a "Latest Articles" section limited to published content.

## Technical Context

**Language/Version**: Python 3.14+, TypeScript 5.x  
**Primary Dependencies**: Next.js 14 (App Router), Tailwind CSS, Shadcn UI  
**Storage**: Supabase (Read-only `status='published'` query)  
**Testing**: Vitest (query logic), Playwright (Visual check)  
**Target Platform**: Web (Responsive)  
**Performance Goals**: First Contentful Paint (FCP) < 1.2s  
**Constraints**: Must strictly show only `published` articles (Business rule).  
**Scale/Scope**: UI/UX Refinement + Public API  

## Constitution Check

- **Glue Coding**: PASSED. Reusing Shadcn/Tailwind.
- **Test-First**: PASSED. Plan includes verifying `published` only logic.
- **Security First**: PASSED. Public API is read-only and restricted to published status.
- **Continuous Sync**: PASSED. Branch and context updated.

## Project Structure

### Documentation

```text
specs/034-portal-refinement/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md (Next phase)
```

### Source Code

```text
backend/
├── app/
│   └── api/v1/
│       └── portal.py           # New public endpoints
frontend/
├── src/
│   ├── components/portal/
│   │   ├── HomeBanner.tsx      # New component
│   │   ├── SiteFooter.tsx      # New component
│   │   └── ArticleList.tsx     # New component (Public)
│   ├── app/page.tsx            # Updated Homepage
│   └── app/layout.tsx          # Updated Layout (Footer inclusion)
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |