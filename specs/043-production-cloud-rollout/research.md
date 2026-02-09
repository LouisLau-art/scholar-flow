# Research: Cloud Rollout Regression (GAP-P0-02)

## Research Scope

围绕 “Feature 042 云端迁移与真实环境回归” 的实现，聚焦以下问题：
- 上线验收应采用脚本、API，还是两者结合。
- 验收历史如何持久化，才能满足可追溯与重复执行对比。
- 如何判定“测试跳过”在放行时的阻塞策略。
- 如何在不暴露敏感信息的前提下开放内部验收能力。
- 回退指引应以何种形式标准化，避免人工口头流程。

## Decisions

### 1. 采用“Internal API + CLI 脚本”双入口

- **Decision**: 以 `internal` 受保护 API 提供验收编排能力，同时提供脚本封装调用，供发布流程一键执行。
- **Rationale**: API 便于审计和系统化集成；脚本便于日常执行与 CI-like 场景复用。
- **Alternatives considered**:
  - 仅脚本：执行方便但缺乏结构化结果与统一审计入口。
  - 仅 API：可观测性好，但运维执行门槛偏高。

### 2. 验收历史采用独立记录表持久化

- **Decision**: 新增 `release_validation_runs` 与 `release_validation_checks` 两层记录，分别保存“执行批次”和“检查项明细”。
- **Rationale**: 能支持重复执行、差异对比、责任追溯，不污染业务状态日志。
- **Alternatives considered**:
  - 仅写日志文件：难查询、难对比、跨环境不可追踪。
  - 复用 `status_transition_logs`：语义不匹配，字段约束与查询模型不理想。

### 3. 放行策略采用“阻塞优先 + skip 归零”

- **Decision**: 任一阻塞项失败即整体失败；关键回归场景中若出现 skip，则不允许放行。
- **Rationale**: 该特性目标是“云端真实可用性”，skip 会掩盖环境缺陷，必须强约束。
- **Alternatives considered**:
  - 允许部分失败放行：短期提速，但显著提高线上事故风险。
  - 仅统计失败不统计 skip：无法识别“未验证即放行”的风险。

### 4. 安全控制沿用 `ADMIN_API_KEY` 内部保护

- **Decision**: 所有验收执行与报告读取接口均放在 `/api/v1/internal/*`，并要求 `ADMIN_API_KEY`。
- **Rationale**: 与现有内部运维端点一致，最小改动即可达到权限隔离目标。
- **Alternatives considered**:
  - 新建独立认证体系：改造成本高，超出本特性范围。
  - 沿用普通用户 JWT：权限颗粒度不足，存在误触发风险。

### 5. 回退方案采用“模板化步骤 + 结果留痕”

- **Decision**: 在验收报告中内置标准回退步骤模板，并记录回退执行状态与责任人。
- **Rationale**: 让失败处理从“经验驱动”转为“流程驱动”，减少临场决策风险。
- **Alternatives considered**:
  - 仅文档说明回退：可读但不可审计。
  - 仅口头流程：无追踪记录，复盘困难。

## Resolved Clarifications

本阶段不存在未解决的 `NEEDS CLARIFICATION` 项。  
核心设计选择均已明确，可进入数据模型与接口合同设计。
