# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app, core services, and pytest suite.
  - `backend/app/api/v1/` API routes (manuscripts, editor, reviews, stats).
  - `backend/app/core/` auth, AI, PDF, and worker utilities.
  - `backend/app/models/` Pydantic v2 schemas.
  - `backend/tests/` unit/integration/contract tests.
- `frontend/`: Next.js App Router app plus tests.
  - `frontend/src/app/` pages and routes.
  - `frontend/src/components/` UI components.
  - `frontend/src/lib/` API client and Supabase config.
  - `frontend/tests/` Playwright E2E + Vitest unit tests.
- `specs/` and `.specify/`: product specs and task breakdowns.

## Build, Test, and Development Commands
- Backend run: `uvicorn main:app --reload` (from `backend/`).
- Backend tests: `pytest` or `pytest --cov=src --cov-report=html`.
- Frontend dev: `pnpm dev` (from `frontend/`).
- Frontend unit tests: `npm run test` (Vitest).
- Frontend E2E: `npm run test:e2e` (Playwright).
- All tests: `./scripts/run-all-tests.sh`.
- Coverage: `./scripts/generate-coverage-report.sh`.

## Coding Style & Naming Conventions
- Python: snake_case, type hints required.
- TypeScript/React: camelCase; prefer explicit types for API payloads.
- Core logic must include **Chinese comments** (security, algorithms, workflows).
- Use project tooling (`ruff check .`, `pnpm lint`) before PRs.
- Environment: Arch Linux; prefer `pacman` then `paru` for deps.

## Testing Guidelines
- Frameworks: pytest/pytest-cov (backend), Vitest (frontend), Playwright (E2E).
- Authentication-required endpoints must be tested for valid, missing, and invalid tokens.
- Prefer real DB integration tests when `SUPABASE_URL`/`SUPABASE_KEY` are set.
- Test files follow `test_*.py` / `*.spec.ts` naming.

## Commit & Pull Request Guidelines
- Commit style follows Conventional Commits (e.g., `docs: ...`, `chore: ...`).
- Keep commits small and scoped to one task (≤5 files per atomic change).
- PRs should describe scope, link related specs/issues, and include screenshots for UI changes.

## Agent-Specific Notes
- Follow `.specify/memory/constitution.md` and `specs/*/tasks.md`.
- After each atomic task, push to GitHub to create a savepoint.

## Active Technologies
- Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, pytest, Playwright, Vitest, Supabase-js v2.x, Supabase-py v2.x (009-test-coverage)
- PostgreSQL (Supabase) (009-test-coverage)

## Recent Changes
- 009-test-coverage: Added Python 3.14+, TypeScript 5.x, Node.js 20.x + FastAPI 0.115+, Pydantic v2, pytest, Playwright, Vitest, Supabase-js v2.x, Supabase-py v2.x
