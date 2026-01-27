# Implementation Plan: Manuscript Plagiarism Check

**Branch**: `002-plagiarism-check` | **Date**: 2026-01-27 | **Spec**: [specs/002-plagiarism-check/spec.md]

## Summary
实现稿件提交后的自动异步查重流程。后端 FastAPI 接收提交信号后，通过后台任务（Background Tasks）调用 Crossref/iThenticate API 进行全文比对，获取相似度得分并生成 PDF 报告。系统需处理高重复率（>30%）拦截、自动通知编辑以及异常重试/手动重试逻辑。

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript (Next.js 14.2)
**Primary Dependencies**: 
- Backend: FastAPI 0.115+, Pydantic v2, `httpx` (异步 API 调用), `python-jose` (JWT 校验)
- Frontend: Tailwind CSS 3.4, Shadcn UI
**Storage**: Supabase (PostgreSQL) - `PlagiarismReports` 表, Supabase Storage - `plagiarism-reports` 存储桶
**Testing**: pytest
**Target Platform**: Linux / Docker
**Environment**: 
- 开发平台锁定为 **Arch Linux**。
- 包安装遵循 `pacman` > `paru` (切换至用户 `louis` 执行) > `pip`/`pnpm` 优先级。
- Python 全局包安装必须包含 `--break-system-packages` 参数。
- Docker 必须配置国内镜像源。
**Performance Goals**: 查重启动 < 5min, 结果返回（取决于 API）建议 < 30min
**Constraints**: 
- 必须异步处理，不阻塞主流程。
- 3 次自动重试失败后需进入手动重试模式。
- 严格遵守 v1.4.0 视觉标准与架构规范。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **治理合规 (SD/PG)**: 是。具备完整 spec，严格执行 0->1->2 序列。
2. **交付模型 (TI/MVP)**: 是。拆分为触发、预警、管理三个独立 Story。
3. **架构与版本**: 是。FastAPI 0.115, Pydantic v2, Next.js 14.2。
4. **数据流规范**: 是。查重逻辑显性化，前端 API 统一封装。
5. **容错机制**: 是。包含 3 次自动重试及“手动重试”幂等设计。
6. **视觉标准**: 是。管理后台按钮与报告列表符合 `slate-900` 风格。
7. **AI 协作**: 是。任务原子化拆分，关键算法包含中文注释计划。

## Project Structure

### Documentation (this feature)

```text
specs/002-plagiarism-check/
├── plan.md              # 本文件
├── research.md          # API 调研与异步队列方案
├── data-model.md        # PlagiarismReports 表定义
├── quickstart.md        # 查重流程验证用例
├── contracts/           # 查重 API 契约
└── tasks.md             # 任务列表
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/v1/          # 查重触发与状态查询接口
│   ├── core/            # 异步任务调度 (plagiarism_worker.py)
│   └── services/        # Crossref API 集成封装 (crossref_client.py)
└── tests/

frontend/
├── src/
│   ├── components/      # 查重报告下载组件, 手动重试按钮
│   └── app/admin/       # 编辑查看查重状态页面
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |