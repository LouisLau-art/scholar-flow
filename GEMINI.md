# scholar-flow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-27

## Active Technologies
- **Frontend**: TypeScript, Next.js 14.2 (App Router), Tailwind CSS 3.4, Shadcn UI
- **Backend**: Python 3.11+, FastAPI 0.115+, Pydantic v2, httpx
- **Database & Auth**: Supabase (PostgreSQL), Supabase Auth
- **Storage**: Supabase Storage (`manuscripts`, `plagiarism-reports` buckets)
- **AI/ML**: OpenAI SDK (GPT-4o), scikit-learn (TF-IDF matching)

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/          # FastAPI Routes (Manuscripts, Reviews, Plagiarism)
│   ├── core/            # Business Logic & Workers (AI Engine, PDF Processor, Workers)
│   ├── models/          # Pydantic v2 Schemas
│   └── services/        # Third-party Integrations (Crossref Client, Editorial)
├── scripts/             # Verification & Utility Scripts
└── tests/               # Pytest Suite

frontend/
├── src/
│   ├── app/             # Next.js App Router (submit, admin, finance, review)
│   ├── components/      # UI Components (SubmissionForm, PlagiarismActions, etc.)
│   ├── lib/             # API Client & Supabase Config
│   └── types/           # TypeScript Interfaces
└── tests/               # Vitest/Playwright
```

## Commands
- **Backend**: `uvicorn main:app --reload`
- **Frontend**: `pnpm dev`
- **Linting**: `ruff check .` (Backend), `pnpm lint` (Frontend)
- **Database**: `supabase migration new [name]`

## Code Style
- **Naming**: camelCase for Frontend, snake_case for Backend.
- **Comments**: Mandatory **Chinese comments** for core logic (algorithms, security).
- **Architecture**: Server Components first, unified API client encapsulation.

## Recent Changes
- 002-plagiarism-check: Async plagiarism check with similarity gate (0.3).
- 001-core-workflow: Full submission lifecycle with EIC publication gate.

<!-- MANUAL ADDITIONS START -->
- Environment: Arch Linux (pacman/paru priority).
- Savepoints: Push to GitHub after every atomic task (v1.6.0 Constitution).
<!-- MANUAL ADDITIONS END -->