# Fast-Track Quality Checklist: Manuscript Plagiarism Check

**Purpose**: 极简版预执行清单，旨在确保 002 功能在快速上线的目标下依然满足核心质量与合宪性要求。
**Created**: 2026-01-27
**Feature**: [specs/002-plagiarism-check/spec.md]

## 核心业务闭环 (MVP Readiness)
- [x] CHK001 是否明确了外部 API 调用失败后的“手动重试”交互逻辑？ [Clarity, Spec §Edge Cases]
- [x] CHK002 是否定义了相似度得分 > 0.3 时的自动拦截规则？ [Completeness, Spec §FR-004]
- [x] CHK003 查重报告 PDF 的存储桶是否已配置为“私有”且支持签名下载？ [Security, Plan]

## 合宪性与环境适配 (Constitution Alignment)
- [x] CHK004 安装 `python-httpx` 任务是否明确了 `pacman` 优先原则？ [Consistency, Tasks §T001]
- [x] CHK005 涉及 API 客户端与 Worker 的任务是否包含“中文注释”要求？ [Constitution VII, Tasks §Notes]
- [x] CHK006 任务列表是否包含 Phase 结尾的 `git push` 存档点？ [Constitution IX, Tasks]

## 关键技术点验证 (Risk Mitigation)
- [x] CHK007 异步 Worker 是否定义了基础的限流 (Rate Limiting) 逻辑以防止被封禁？ [Coverage, Tasks §T009a]
- [x] CHK008 数据库表是否包含 `manuscript_id` 唯一索引以防止重复查重？ [Consistency, Data Model]