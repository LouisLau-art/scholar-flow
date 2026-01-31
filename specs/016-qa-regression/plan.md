# Implementation Plan - Comprehensive QA & E2E Regression

**Feature**: Feature 016 - Comprehensive QA & E2E Regression
**Status**: COMPLETED (Implemented on 2026-01-30)

## Technical Context

This feature establishes a comprehensive Quality Assurance baseline for the Scholar-Flow platform following the merger of two major features (CMS and Academic Indexing). It focuses on End-to-End (E2E) regression testing using Playwright to validate critical user journeys across the integrated system.

**Key Technical Components:**

1.  **Testing Framework**: Playwright (TypeScript) for E2E testing, as established in the project stack.
2.  **Test Environment**:
    *   **Database**: Needs a mechanism to reset/seed data (Ephemeral DB).
    *   **Backend**: FastAPI server running locally or in CI.
    *   **Frontend**: Next.js application running locally or in CI.
3.  **Mocking Strategy**:
    *   **External APIs**: Crossref (DOI) and potentially OpenAI (Matchmaking) need to be mocked to ensure deterministic tests and avoid external dependencies/costs.
    *   **Mocking Level**: Service-level mocking in Python (e.g., swapping `CrossrefClient` with `MockCrossrefClient`) is preferred over network interception for better stability and testing internal logic.
4.  **Integration Points**:
    *   **CMS**: Database tables `cms_pages`, `cms_menu_items` and API endpoints.
    *   **DOI**: Database tables `doi_registrations`, `doi_tasks` and background worker.
    *   **Workflow**: Interaction between `manuscripts`, `reviews`, and `users` tables.

**Unknowns & Clarifications:**

*   [X] **Research Task 1**: Verify the existing E2E test setup (Playwright) configuration and helper functions. Ensure we have the necessary utilities for database resetting/seeding.
*   [X] **Research Task 2**: Determine the best way to inject mock services (Crossref, OpenAI) into the running FastAPI application during E2E tests. (Dependency injection overrides vs. environment variable toggles).
*   [X] **Research Task 3**: Analyze the current database migration state to ensure `cms` and `doi` tables are correctly defined and no conflicts exist (confirming the fix for `articles` vs `manuscripts` table reference).

## Constitution Check

> [!IMPORTANT]
> Verify alignment with `.specify/memory/constitution.md` principles.

*   **Principle 1 (Library-First)**: N/A - This is a QA/Testing feature, not a new library. However, test utilities should be modular.
*   **Principle 2 (CLI Interface)**: N/A.
*   **Principle 3 (Test-First)**: **CRITICAL**. This entire feature IS about testing. We are defining the tests (E2E scenarios) that *define* the expected behavior of the system. We are essentially writing the "ultimate acceptance tests".
*   **Principle 4 (Integration Testing)**: This feature implements the Integration/E2E testing layer.
*   **Principle 5 (Observability)**: Test results and artifacts (screenshots/traces) must be observable in CI.

**Compliance Assessment**:
*   The plan directly supports Principle 3 and 4 by hardening the testing infrastructure.
*   No violations detected.

## Phase 0: Research & Validation

**Goal**: Resolve technical unknowns and validate the integration state.

*   [ ] **Research**: Audit existing Playwright setup and identify missing helpers (e.g., DB reset).
*   [ ] **Research**: Prototype the service-level mocking strategy for FastAPI (how to swap `CrossrefClient` in a running app).
*   [ ] **Research**: Inspect the merged database schema (013 + 015) to confirm referential integrity.
*   [ ] **Output**: `specs/016-qa-regression/research.md` with decisions on mocking and DB seeding.

## Phase 1: Design & Specification

**Goal**: Define the test data model and API contracts (if any new test-support APIs are needed).

*   [ ] **Data Model**: Define the "Seed Data" schema (Users, Journals, Standard Manuscripts) for the E2E suite.
*   [ ] **Contracts**: Define any "Test Support APIs" needed (e.g., `POST /api/test/reset-db` if we choose an API-driven reset approach).
*   [ ] **Plan**: Detail the exact E2E test scenarios (files and test cases) to be implemented.
*   [ ] **Output**: `data-model.md` (for seed data), `contracts/` (if needed), updated `plan.md`.

## Phase 2: Implementation Breakdown

**Goal**: Implement the test suite and fix discovered bugs.

### Step 1: Test Infrastructure
*   **Task**: Implement DB Reset/Seed mechanism (Script or API endpoint).
*   **Task**: Implement Service Mocking (Dependency Injection overrides).
*   **Task**: Configure Playwright for the new environment (Base URL, Auth setup).

### Step 2: Critical User Journeys (CUJs)
*   **Task**: Implement **Author Flow** (Register -> Submit).
*   **Task**: Implement **Editor Flow** (Assign -> Decide -> Publish).
*   **Task**: Implement **CMS Flow** (Create Page -> View).
*   **Task**: Implement **DOI Flow** (Publish -> Verify Registration Task).
*   **Task**: Implement **AI Matchmaker Test** (Verify Suggestions Load).

### Step 3: Bug Fixing & Stabilization
*   **Task**: Run the full suite and identify failures.
*   **Task**: Fix bugs in the application code (Frontend/Backend) exposed by tests.
*   **Task**: Fix UI glitches (Z-index, Mobile layout).

### Step 4: Final Polish
*   **Task**: Standardize error messages.
*   **Task**: Ensure test coverage > 80% for core services.
*   **Task**: Final CI Run.

## Phase 3: Verification & Launch

*   **Goal**: Ensure all tests pass reliably in CI.
*   **Verification**: Run the full suite 3 times to check for flakiness.
*   **Launch**: Merge `016-qa-regression` to `master`.
