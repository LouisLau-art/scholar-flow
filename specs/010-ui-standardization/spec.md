# Feature Specification: UI Standardization and Fixes

**Feature Branch**: `010-ui-standardization`
**Created**: 2026-01-30
**Status**: Complete
**Input**: User description: "1. 全局审计（找出所有潜在白字白底） - 扫描 frontend/src 里所有 text-white、text-slate-50、bg-white、bg-slate-50 的组合，尤其是 button/div 里带状态的类。 - 标记：凡是“未选中状态”没有显式 text color 的全部列入修复清单。 2. 统一交互组件为 Shadcn/UI - 所有按钮 → Button 组件（default/outline/ghost） - 所有“选中/未选中卡片按钮” → RadioGroup + Label（或 ToggleGroup） - 所有 Tabs/选择项 → TabsTrigger + data-[state=active] 管理 - 禁止再用 div + className 手搓点击卡片 3. 定义清晰的状态样式（默认、hover、active、disabled） - 默认：text-slate-900 bg-white border-slate-200 - 选中：text-white bg-slate-900 或 bg-blue-600 - hover：bg-slate-50 - disabled：text-slate-400 bg-slate-100 - 所有状态类集中在组件内部，不散落在页面中。 4. 逐模块修复（高风险优先） - DecisionPanel 的 Accept/Reject 选项（当前就是白字白底最典型） - Reviewer modal（评分/提交区域） - Editor Pipeline / Assign Modal / Editor tabs - 其它页面中的“自定义按钮” 5. 回归验证 - 人工快速走一次 Author/Reviewer/Editor 关键页 - ./run_tests.sh 保持全绿"

## Clarifications

### Session 2026-01-30
- Q: 范围排除 (Exclusions) → A: 排除复杂组件（如图表、可视化插件），仅处理标准 UI 元素
- Q: 状态优先级 (State Precedence) → A: 选中状态优先级高于悬停状态
- Q: 暗黑模式策略 (Dark Mode Strategy) → A: 强制浅色模式（暂不支持暗黑模式切换）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Legibility (Priority: P1)

Users (Authors, Editors, Reviewers) need to clearly read all text in the interface, ensuring no text is invisible due to poor contrast (e.g., white text on white background) regardless of the element's state.

**Why this priority**: Essential for usability. Invisible text prevents users from understanding and using the application.

**Independent Test**: Can be tested by navigating to the "DecisionPanel" and "Reviewer modal" and verifying all text is visible in both selected and unselected states.

**Acceptance Scenarios**:

1. **Given** a decision panel with "Accept" and "Reject" options, **When** the options are unselected, **Then** the text color must contrast with the background (e.g., dark text on light background).
2. **Given** a decision panel, **When** an option is selected, **Then** the text color must contrast with the active background (e.g., white text on dark background).
3. **Given** any interactive element, **When** in a "disabled" state, **Then** it must be clearly visible but visually distinct from enabled states (e.g., greyed out).

---

### User Story 2 - Standardized Interactions (Priority: P2)

Users interact with buttons, tabs, and selection cards that look and behave consistently across the application, leveraging a unified design system.

**Why this priority**: Improves user experience and reduces cognitive load by making interactions predictable. Reduces maintenance burden by unifying components.

**Independent Test**: Can be tested by clicking buttons and tabs in the Editor Dashboard and verifying they look and behave identically to those in other parts of the app.

**Acceptance Scenarios**:

1. **Given** any button in the application (e.g., "Submit", "Cancel"), **When** rendered, **Then** it uses the standard Shadcn Button component styles.
2. **Given** a set of mutually exclusive options (e.g., card selection), **When** interacting, **Then** it behaves as a RadioGroup or ToggleGroup with standard active/inactive styles.
3. **Given** a tabbed interface, **When** switching tabs, **Then** the active tab is highlighted using standard state styles.

---

### Edge Cases

- What happens when a button is in a loading state? (Should likely use standard Shadcn loading state).
- How does the system handle elements that must deviate from the standard theme for specific branding reasons? (Currently, strict adherence to Shadcn is required).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ensure all text elements have a contrast ratio compliant with accessibility standards (specifically fixing white-on-white).
- **FR-002**: System MUST use Shadcn `Button` component for all clickable button actions, replacing custom `div` or `button` implementations.
- **FR-003**: System MUST use `RadioGroup` or `ToggleGroup` components for all "select one of many" card interfaces.
- **FR-004**: System MUST use `Tabs` and `TabsTrigger` components for all tabbed interfaces, managing state via `data-[state=active]`.
- **FR-005**: System MUST implement a unified style set for interactive states:
    - Default: `text-slate-900 bg-white border-slate-200`
    - Selected/Active: `text-white bg-slate-900` (or `bg-blue-600` for primary actions)
    - Hover: `bg-slate-50`
    - Disabled: `text-slate-400 bg-slate-100`
    - **Precedence**: Selected/Active state MUST visually override Hover state (e.g., if selected, hovering should not revert background to light grey).
- **FR-006**: System MUST centralize state styles within components, preventing ad-hoc style application in page layouts.
- **FR-007**: System MUST prioritize repairs on "DecisionPanel", "Reviewer Modal", and "Editor Pipeline" modules.
- **FR-008**: Complex components (e.g., charts, visualization plugins) are EXPLICITLY OUT OF SCOPE; only standard UI elements are handled.
- **FR-009**: System MUST enforce Light Mode styles only (dark mode is explicitly out of scope for this feature).

### Security & Authentication Requirements *(mandatory)*

- **SEC-001**: All sensitive operations MUST require authentication (Principle XIII).
- **SEC-002**: API endpoints MUST validate JWT tokens on every request (Principle XIII).
- **SEC-003**: Use real user IDs from authentication context, NEVER hardcoded or simulated IDs (Principle XIII).
- **SEC-004**: Implement proper RBAC (Role-Based Access Control) for different user types (Principle XIII).
- **SEC-005**: Security considerations MUST be addressed during initial design (Principle XIII).

### API Development Requirements *(mandatory)*

- **API-001**: Define API specification (OpenAPI/Swagger) BEFORE implementation (Principle XIV).
- **API-002**: Use consistent path patterns (no trailing slashes unless necessary) (Principle XIV).
- **API-003**: Always version APIs (e.g., `/api/v1/`) (Principle XIV).
- **API-004**: Every endpoint MUST have clear documentation (Principle XIV).
- **API-005**: Implement unified error handling with middleware (Principle XIV).
- **API-006**: Provide detailed logging for all critical operations (Principle XIV).

### Test Coverage Requirements *(mandatory)*

- **TEST-001**: Test ALL HTTP methods (GET, POST, PUT, DELETE) for every endpoint (Principle XII).
- **TEST-002**: Ensure frontend and backend API paths match EXACTLY (Principle XII).
- **TEST-003**: Every authenticated endpoint MUST have tests for valid/missing/invalid authentication (Principle XII).
- **TEST-004**: Test all input validation rules (required fields, length limits, format constraints) (Principle XII).
- **TEST-005**: Test error cases, not just happy paths (Principle XII).
- **TEST-006**: Include integration tests using REAL database connections (Principle XII).
- **TEST-007**: Achieve 100% test pass rate before delivery (Principle XI).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero occurrences of "white text on white background" in the `frontend/src` directory, verified by visual inspection of critical paths.
- **SC-002**: All buttons and card selectors in "DecisionPanel", "Reviewer Modal", and "Editor Pipeline" are refactored to use Shadcn components.
- **SC-003**: Visual regression tests (or manual verification) confirm distinct styles for Default, Hover, Active, and Disabled states on all modified components.
- **SC-004**: The project's full test suite (`./run_tests.sh`) passes with 100% success rate.

## Implementation Notes (2026-01-30)

- Shadcn config added (`components.json`) with CSS variables and Light Mode enforcement in `globals.css`.
- Core primitives added: `Button`, `Card`, `Label`, `RadioGroup`; `Tabs` updated to use theme tokens.
- DecisionPanel refactored to RadioGroup + Button to eliminate white-on-white states.
- Reviewer review modal and Editor Dashboard tabs standardized to Shadcn components.
- Editor Pipeline cards now support click-to-filter + Clear Filter for faster navigation.
- Tests: `npm run test` (frontend) and `./run_tests.sh` (full suite).
