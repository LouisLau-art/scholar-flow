# Feature Specification: Refine Portal Home and Navigation

**Feature Branch**: `034-portal-refinement`  
**Created**: 2026-02-04  
**Status**: Draft  
**Input**: User description: "启动 Feature 034 (首页与门户微调)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Academic Identity Banner (Priority: P1)

As a Visitor, I want to see a professional academic banner on the homepage that includes the journal title, ISSN, and key metrics (Impact Factor placeholder), so that I immediately recognize this as a legitimate scholarly venue.

**Why this priority**: First impressions are critical for trust (PDF P1 requirement).

**Independent Test**: Visit the homepage `/` and verify the Banner section contains Title, Description, ISSN, and Impact Factor.

**Acceptance Scenarios**:

1. **Given** I am on the homepage, **When** I look at the top banner, **Then** I see the journal name, ISSN, and a "Submit Manuscript" call-to-action.
2. **Given** the banner, **When** I click "Submit Manuscript", **Then** I am navigated to the submission wizard (or login if unauthenticated).

---

### User Story 2 - Standardized Footer (Priority: P2)

As a Visitor, I want to see a standardized footer with Copyright, Links (About, Contact), and ISSN on every page, so that I can easily navigate and verify the site's ownership.

**Why this priority**: Essential for site-wide navigation and professional completeness (PDF P1).

**Independent Test**: Navigate to any public page (Home, Article, Login) and verify the footer exists and contains the required links.

**Acceptance Scenarios**:

1. **Given** the footer, **When** I verify the content, **Then** I see "Copyright © 202X ScholarFlow", "ISSN: XXXXX", and links to "About" and "Contact".

---

### User Story 3 - Latest Articles Showcase (Priority: P2)

As a Visitor, I want to see a "Latest Articles" section on the homepage that displays only **published** manuscripts, so that I can access the latest research.

**Why this priority**: Drives readership and showcases content value.

**Independent Test**: Publish a manuscript (via Editor flow) and verify it appears in the "Latest Articles" section on the homepage. Unpublish/Reject it and verify it disappears.

**Acceptance Scenarios**:

1. **Given** the homepage, **When** I scroll to "Latest Articles", **Then** I see a list of manuscripts with status `Published`.
2. **Given** a manuscript in `Accepted` or `Proofreading` status, **When** I check the homepage, **Then** it does NOT appear in "Latest Articles".

---

### Edge Cases

- **Mobile View**: Does the banner scale down gracefully? (Assumption: Stack metrics vertically on mobile).
- **No Published Articles**: What if the system is empty? (Assumption: Hide the section or show "Coming Soon").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Homepage Banner MUST display: Journal Title, Description, ISSN, Impact Factor (static placeholder), and a primary "Submit Manuscript" button.
- **FR-002**: The "Submit Manuscript" button MUST redirect to `/submit` (triggering auth if needed).
- **FR-003**: The Site Footer MUST display: Copyright Year, Journal Name, ISSN, and navigation links (Home, About, Contact, Login/Dashboard).
- **FR-004**: The Homepage MUST include a "Latest Articles" section querying only manuscripts with `status = 'published'`.
- **FR-005**: The "Latest Articles" cards MUST display: Title, Authors (truncated), Abstract (truncated), and Published Date.
- **FR-006**: The Navbar MUST provide clear distinct entry points for "Submit Manuscript" vs "Login" (if anonymous).

### Key Entities

- **Manuscript**: Querying `published` status for the showcase.
- **Journal Metadata**: Static config (ISSN, Title).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Visitors can locate the "Submit Manuscript" button within 3 seconds of landing on the homepage.
- **SC-002**: 100% of articles displayed in "Latest Articles" have `status='published'`.
- **SC-003**: The homepage matches the visual structure of reference PDF P1 (professional academic theme).

## OJS/Janeway 对标映射

- **Portal 入口分层**：对齐 OJS/Janeway 的公开门户信息架构，保持 `Journals / Topics / Submit / About` 明确分区，避免“编辑后台入口”混入公开导航。
- **Latest Articles 发布约束**：对齐两者“仅公开已发布内容”的基线，禁止 `approved/proofreading` 等中间态出现在公开流。
- **引用/检索友好**：与 Janeway 的 Scholar 友好实践一致，要求文章卡片与详情在公开页保持 DOI/发布日期语义一致，避免元数据割裂。
