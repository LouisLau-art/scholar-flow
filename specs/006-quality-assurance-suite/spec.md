# Feature Specification: Quality Assurance Suite

**Feature Branch**: `006-quality-assurance-suite`
**Created**: 2026-01-27
**Status**: Draft

## Goals
建立一套全自动化的质量保证体系，涵盖后端 API 契约测试、前端组件渲染测试以及核心业务流程的冒烟测试。

## User Scenarios

### US1: 自动回归测试 (Automated Regression)
- **Scenario**: 每次修改后端代码时, **I want** 运行测试指令, **So that** 我能确信没有破坏现有的 API 接口（如上传、搜索）。
- **Requirements**:
  - 后端接口测试覆盖率 > 70%。
  - 支持一键运行所有测试用例并输出报告。

### US2: 交互与渲染验证 (UI Component Integrity)
- **Scenario**: 每次修改 UI 组件时, **I want** 自动化脚本验证组件状态, **So that** 我能确保按钮点击、Toast 弹出等逻辑依然正常。
- **Requirements**:
  - 覆盖登录、投稿表单、查重操作组件的核心逻辑。

### US3: 业务边界校验 (Edge Case Validation)
- **Scenario**: 作为开发者, **I want** 模拟异常输入（如空摘要、大文件、无效 Token）, **So that** 验证系统的容错性。
- **Requirements**:
  - 包含对相似度门控（0.3）的边界测试。

## Success Criteria
- [ ] 后端通过 `pytest` 实现对 80% 核心 API 的覆盖。
- [ ] 前端通过 `Vitest` 验证 `SubmissionForm` 的解析填充逻辑。
- [ ] 在 `start.sh` 同级目录下新增 `run_tests.sh` 一键测试脚本。
