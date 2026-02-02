# Data Model: 完善测试覆盖

**Feature Branch**: `009-test-coverage`
**Date**: 2026-01-29
**Input**: Feature specification and research findings

## Overview

This data model defines the test entities and their relationships for the test coverage feature. The model focuses on test organization, execution tracking, and coverage reporting.

## Entities

### 1. Test Suite

**Purpose**: A collection of test cases organized by type and scope

**Fields**:
- `id`: UUID - Unique identifier
- `name`: String - Test suite name (e.g., "Backend API Tests", "E2E Tests")
- `type`: Enum - `unit`, `integration`, `e2e`
- `language`: Enum - `python`, `typescript`
- `framework`: String - Test framework (pytest, playwright, vitest)
- `target_coverage`: Float - Target coverage percentage (0.0 - 1.0)
- `current_coverage`: Float - Current coverage percentage (0.0 - 1.0)
- `status`: Enum - `pending`, `running`, `passed`, `failed`
- `created_at`: Timestamp - Creation time
- `updated_at`: Timestamp - Last update time

**Relationships**:
- Has many: `test_cases` (1:N)
- Has one: `coverage_report` (1:1)

**Validation Rules**:
- `name`: Required, 1-100 characters
- `type`: Required, one of: unit, integration, e2e
- `target_coverage`: Required, 0.0 - 1.0
- `current_coverage`: Optional, 0.0 - 1.0

**State Transitions**:
```
pending → running → passed/failed
```

---

### 2. Test Case

**Purpose**: A single test scenario with preconditions, actions, and expected outcomes

**Fields**:
- `id`: UUID - Unique identifier
- `suite_id`: UUID - Reference to test suite
- `name`: String - Test case name
- `description`: String - Detailed description
- `priority`: Enum - `P1`, `P2`, `P3`
- `category`: Enum - `auth`, `validation`, `error`, `boundary`, `concurrent`, `integration`
- `given`: String - Precondition (Given)
- `when`: String - Action (When)
- `then`: String - Expected outcome (Then)
- `status`: Enum - `pending`, `passing`, `failing`, `skipped`
- `execution_time`: Float - Last execution time in seconds
- `created_at`: Timestamp - Creation time
- `updated_at`: Timestamp - Last update time

**Relationships**:
- Belongs to: `test_suite`
- Has many: `test_executions` (1:N)

**Validation Rules**:
- `name`: Required, 1-200 characters
- `priority`: Required, one of: P1, P2, P3
- `category`: Required, one of: auth, validation, error, boundary, concurrent, integration
- `given`, `when`, `then`: Required, 1-1000 characters

**State Transitions**:
```
pending → passing/failed/skipped
```

---

### 3. Coverage Report

**Purpose**: A snapshot of code coverage metrics

**Fields**:
- `id`: UUID - Unique identifier
- `suite_id`: UUID - Reference to test suite
- `total_statements`: Integer - Total lines of code
- `covered_statements`: Integer - Lines covered by tests
- `total_branches`: Integer - Total code branches
- `covered_branches`: Integer - Branches covered by tests
- `total_functions`: Integer - Total functions/methods
- `covered_functions`: Integer - Functions covered by tests
- `line_coverage`: Float - Line coverage percentage (0.0 - 1.0)
- `branch_coverage`: Float - Branch coverage percentage (0.0 - 1.0)
- `function_coverage`: Float - Function coverage percentage (0.0 - 1.0)
- `generated_at`: Timestamp - Report generation time

**Relationships**:
- Belongs to: `test_suite`
- Has many: `uncovered_files` (1:N)

**Validation Rules**:
- `suite_id`: Required
- All coverage metrics: 0.0 - 1.0

---

### 4. Uncovered File

**Purpose**: A file with uncovered code paths

**Fields**:
- `id`: UUID - Unique identifier
- `coverage_report_id`: UUID - Reference to coverage report
- `file_path`: String - Relative file path
- `total_lines`: Integer - Total lines in file
- `uncovered_lines`: Array<Integer> - Line numbers not covered
- `coverage_percentage`: Float - Coverage for this file (0.0 - 1.0)

**Relationships**:
- Belongs to: `coverage_report`

**Validation Rules**:
- `file_path`: Required, valid file path
- `coverage_percentage`: 0.0 - 1.0

---

### 5. Test Execution

**Purpose**: A single execution of a test case

**Fields**:
- `id`: UUID - Unique identifier
- `test_case_id`: UUID - Reference to test case
- `status`: Enum - `passed`, `failed`, `skipped`
- `duration`: Float - Execution duration in seconds
- `error_message`: String - Error message if failed
- `stack_trace`: String - Stack trace if failed
- `started_at`: Timestamp - Execution start time
- `ended_at`: Timestamp - Execution end time

**Relationships**:
- Belongs to: `test_case`

**Validation Rules**:
- `status`: Required, one of: passed, failed, skipped
- `duration`: Required, >= 0

---

## Entity Relationships

```
Test Suite (1) ──┐
                 │
Test Case (N) ───┼── (1) Test Suite
                 │
Test Execution (N) ── (1) Test Case

Test Suite (1) ──┐
                 │
Coverage Report (1) ── (1) Test Suite
                 │
Uncovered File (N) ── (1) Coverage Report
```

## Key Business Rules

1. **Test Suite Creation**: A test suite must have a target coverage >= 80% for backend, >= 70% for frontend
2. **Test Case Priority**: P1 tests must pass before P2 tests can be executed
3. **Coverage Threshold**: Coverage reports must show >= 80% backend coverage, >= 70% frontend coverage
4. **Execution Order**: Unit tests → Integration tests → E2E tests
5. **Failure Handling**: Any test failure blocks the entire suite from passing

## State Machines

### Test Suite Status
```
pending → running → passed/failed
```

### Test Case Status
```
pending → passing/failed/skipped
```

## Indexes

- `test_suite(name, type)`: For quick lookup by suite type
- `test_case(suite_id, priority)`: For prioritized test execution
- `coverage_report(suite_id, generated_at)`: For historical coverage tracking
- `test_execution(test_case_id, started_at)`: For execution history

## Constraints

1. **Unique Constraints**:
   - Test suite name must be unique per type
   - Test case name must be unique per suite

2. **Foreign Key Constraints**:
   - `test_case.suite_id` → `test_suite.id` (ON DELETE CASCADE)
   - `coverage_report.suite_id` → `test_suite.id` (ON DELETE CASCADE)
   - `test_execution.test_case_id` → `test_case.id` (ON DELETE CASCADE)

3. **Check Constraints**:
   - `target_coverage` BETWEEN 0.0 AND 1.0
   - `current_coverage` BETWEEN 0.0 AND 1.0
   - `line_coverage` BETWEEN 0.0 AND 1.0
   - `branch_coverage` BETWEEN 0.0 AND 1.0
   - `function_coverage` BETWEEN 0.0 AND 1.0
   - `duration` >= 0

## Implementation Notes

### Supabase Tables

```sql
-- Test Suites
CREATE TABLE test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('unit', 'integration', 'e2e')),
    language TEXT NOT NULL CHECK (language IN ('python', 'typescript')),
    framework TEXT NOT NULL,
    target_coverage FLOAT NOT NULL CHECK (target_coverage BETWEEN 0.0 AND 1.0),
    current_coverage FLOAT CHECK (current_coverage BETWEEN 0.0 AND 1.0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'passed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, type)
);

-- Test Cases
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL CHECK (priority IN ('P1', 'P2', 'P3')),
    category TEXT NOT NULL CHECK (category IN ('auth', 'validation', 'error', 'boundary', 'concurrent', 'integration')),
    given TEXT NOT NULL,
    when TEXT NOT NULL,
    then TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'passing', 'failing', 'skipped')),
    execution_time FLOAT CHECK (execution_time >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(suite_id, name)
);

-- Coverage Reports
CREATE TABLE coverage_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    total_statements INTEGER NOT NULL,
    covered_statements INTEGER NOT NULL,
    total_branches INTEGER NOT NULL,
    covered_branches INTEGER NOT NULL,
    total_functions INTEGER NOT NULL,
    covered_functions INTEGER NOT NULL,
    line_coverage FLOAT NOT NULL CHECK (line_coverage BETWEEN 0.0 AND 1.0),
    branch_coverage FLOAT NOT NULL CHECK (branch_coverage BETWEEN 0.0 AND 1.0),
    function_coverage FLOAT NOT NULL CHECK (function_coverage BETWEEN 0.0 AND 1.0),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Uncovered Files
CREATE TABLE uncovered_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coverage_report_id UUID NOT NULL REFERENCES coverage_reports(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    total_lines INTEGER NOT NULL,
    uncovered_lines INTEGER[] NOT NULL,
    coverage_percentage FLOAT NOT NULL CHECK (coverage_percentage BETWEEN 0.0 AND 1.0)
);

-- Test Executions
CREATE TABLE test_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'skipped')),
    duration FLOAT NOT NULL CHECK (duration >= 0),
    error_message TEXT,
    stack_trace TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX idx_test_suites_name_type ON test_suites(name, type);
CREATE INDEX idx_test_cases_suite_priority ON test_cases(suite_id, priority);
CREATE INDEX idx_coverage_reports_suite_time ON coverage_reports(suite_id, generated_at);
CREATE INDEX idx_test_executions_case_time ON test_executions(test_case_id, started_at);
```

### RLS Policies

```sql
-- Enable RLS
ALTER TABLE test_suites ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE coverage_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE uncovered_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_executions ENABLE ROW LEVEL SECURITY;

-- Test suites: Read for all authenticated users
CREATE POLICY "test_suites_read" ON test_suites
    FOR SELECT USING (auth.role() = 'authenticated');

-- Test suites: Write for editors only
CREATE POLICY "test_suites_write" ON test_suites
    FOR ALL USING (
        auth.role() = 'authenticated' AND
        EXISTS (
            SELECT 1 FROM public.users
            WHERE id = auth.uid() AND role = 'editor'
        )
    );

-- Similar policies for other tables...
```

## Migration Strategy

1. **Phase 1**: Create test_suites and test_cases tables
2. **Phase 2**: Create coverage_reports and uncovered_files tables
3. **Phase 3**: Create test_executions table
4. **Phase 4**: Add RLS policies
5. **Phase 5**: Add indexes and constraints

## Testing Considerations

1. **Test Data**: Use fixtures to create test suites and test cases
2. **Cleanup**: Delete test data after each test run
3. **Isolation**: Each test should operate on its own test suite
4. **Validation**: Verify all constraints and relationships work correctly
