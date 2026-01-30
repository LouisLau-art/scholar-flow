# Feature Specification: Local AI Matchmaker

**Feature Branch**: `012-local-ai-matchmaker`
**Created**: 2026-01-30
**Status**: Implemented
**Input**: User description provided in CLI.

## Clarifications

### Session 2026-01-30
- Q: 向量存储和相似度计算选择哪种方案? → A: 使用 Supabase `pgvector` 扩展进行持久化存储和数据库级相似度查询，以确保数据持久性和查询性能。
- Q: 选用哪个预训练模型生成向量? → A: 使用 `all-MiniLM-L6-v2` 轻量级模型，以平衡推理速度和语义匹配准确度。
- Q: "过往审稿记录"具体包含哪些数据用于匹配? → A: 仅提取审稿人过往审过的文章标题，结合研究兴趣进行特征向量建模。
- Q: 默认的相似度推荐阈值设为多少? → A: 默认设为 `0.70`，且该参数应在后端配置中可调。
- Q: 编辑界面一次展示多少个推荐人选? → A: 默认展示匹配度最高的 Top 5 位人选。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI-Powered Reviewer Recommendation (Priority: P1)

As an Editor, I want to request an AI analysis of a manuscript to get a list of recommended reviewers based on semantic similarity, so that I can identify suitable experts without manual keyword searching.

**Why this priority**: Core value proposition of the feature.

**Independent Test**: Submit a manuscript with specific keywords (e.g., "Quantum Computing"), ensure the system has reviewers with matching interests, trigger analysis, and verify those reviewers appear at the top of the list.

**Acceptance Scenarios**:

1. **Given** a manuscript with a Title and Abstract, **When** the Editor clicks "AI Analysis" in the Assign Reviewer panel, **Then** the system asynchronously calculates matches and displays a list of reviewers sorted by Match Score (High to Low).
2. **Given** the analysis is processing, **When** the Editor waits, **Then** a loading state is shown, and the result appears automatically without blocking the UI.
3. **Given** no reviewers exist in the database, **When** analysis is requested, **Then** the system returns a helpful "Insufficient Data" message (Cold Start handling).

---

### User Story 2 - Automated Profile Indexing (Priority: P2)

As a System, I want to automatically generate and store vector embeddings whenever a Reviewer registers or updates their profile, so that the recommendation engine is always up-to-date without manual intervention.

**Why this priority**: Essential for the recommendations to be accurate and include new users.

**Independent Test**: Register a new user as a Reviewer with specific "Research Interests". Immediately trigger an analysis for a matching manuscript and verify the new reviewer is considered.

**Acceptance Scenarios**:

1. **Given** a new user completes registration as a Reviewer, **When** they save their profile, **Then** the system triggers a background task to generate their profile vector.
2. **Given** an existing reviewer updates their "Research Interests", **When** saved, **Then** their vector is re-calculated and updated.

---

### User Story 3 - Seamless Invitation Integration (Priority: P3)

As an Editor, I want to invite a recommended reviewer directly from the recommendation list, so that I can act on the insights immediately.

**Why this priority**: connects the insight (Matchmaker) to the action (Notification Center).

**Independent Test**: In the AI recommendation list, click "Invite" on a reviewer and verify the standard invitation flow (Feature 011) is triggered.

**Acceptance Scenarios**:

1. **Given** a list of recommended reviewers, **When** the Editor clicks "Invite" on a card, **Then** the system initiates the invitation process (sending the email defined in Feature 011).

---

### Edge Cases

- **Cold Start**: If the system has fewer than a configurable threshold of reviewers (e.g., 5), AI analysis should be disabled or show a specific warning.
- **Empty Manuscript Metadata**: If a manuscript lacks an abstract, the system should fall back to using only the Title or prompt the user.
- **Model Failure**: If the local embedding model fails to load or process, the system must log the error and show a user-friendly "Analysis Unavailable" message, not crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate semantic vector embeddings for Manuscript content (Title + Abstract) using the `all-MiniLM-L6-v2` model from `sentence-transformers`.
- **FR-002**: System MUST generate semantic vector embeddings for Reviewer profiles (Interests + Review History).
- **FR-003**: System MUST use Supabase `pgvector` to store embeddings and calculate Cosine Similarity between Manuscript vectors and Reviewer vectors via SQL queries.
- **FR-004**: System MUST strictly perform all NLP computations locally (NO external calls to OpenAI/Claude/etc.).
- **FR-005**: 计算 MUST 以“非阻塞”的方式执行：索引使用 `BackgroundTasks`（fire-and-forget）；分析请求可同步返回结果，但必须在后台线程/线程池中执行向量化计算，避免阻塞事件循环与 UI。
- **FR-006**: The "AI Analysis" UI MUST be integrated into the existing "Assign Reviewer" workflow (Editor Command Center).
- **FR-007**: System MUST support configurable parameters for the matching algorithm (default threshold: `0.70`, max results: `5`) via configuration, not hardcoded.

### Security & Authentication Requirements *(mandatory)*

- **SEC-001**: All sensitive operations MUST require authentication (Principle XIII).
- **SEC-002**: API endpoints MUST validate JWT tokens on every request (Principle XIII).
- **SEC-003**: Use real user IDs from authentication context, NEVER hardcoded or simulated IDs (Principle XIII).
- **SEC-004**: Implement proper RBAC (Editor only for analysis) (Principle XIII).
- **SEC-005**: Reviewer privacy must be preserved; embedding vectors should not be exposed via public APIs.

### API Development Requirements *(mandatory)*

- **API-001**: Define API specification (OpenAPI/Swagger) BEFORE implementation (Principle XIV).
- **API-002**: Use consistent path patterns (e.g., `/api/v1/matchmaking/analyze`) (Principle XIV).
- **API-003**: Always version APIs (e.g., `/api/v1/`) (Principle XIV).
- **API-004**: Every endpoint MUST have clear documentation (Principle XIV).
- **API-005**: Implement unified error handling with middleware (Principle XIV).
- **API-006**: Provide detailed logging for all critical operations (Principle XIV).

### Test Coverage Requirements *(mandatory)*

- **TEST-001**: Test ALL HTTP methods for matchmaking endpoints (Principle XII).
- **TEST-002**: Ensure frontend and backend API paths match EXACTLY (Principle XII).
- **TEST-003**: Authenticated endpoints MUST have tests for valid/missing/invalid authentication (Principle XII).
- **TEST-004**: Test input validation (e.g., empty abstract) (Principle XII).
- **TEST-005**: Test error cases (e.g., model loading failure) (Principle XII).
- **TEST-006**: Include integration tests using REAL database connections (Principle XII).
- **TEST-007**: Achieve 100% test pass rate before delivery (Principle XI).

### Key Entities

- **ReviewerEmbedding**: Stores the vector representation of a reviewer's expertise. Linked to `auth.users`.
- **ManuscriptEmbedding**: (Optional cache) Stores the vector representation of a manuscript. Linked to `manuscripts`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Recommendation analysis returns results in under 5 seconds (P95) for a database of <1000 reviewers.
- **SC-002**: System makes ZERO external HTTP calls for NLP processing (Verified by audit).
- **SC-003**: New Reviewer profiles are indexed (vectorized) within 60 seconds of registration/update.
- **SC-004**: Cold start scenario (< 5 reviewers) is handled gracefully with a UI message.
