# ScholarFlow 项目交接文档 (2026-01-31 更新)

本文件旨在为后续接手的 AI 助手提供当前项目的完整状态上下文。

## 🚀 最新进展

### 1. UAT 验收测试与预发布环境 (Staging) Setup ✅ (本次完成)
- **环境隔离**: 实现了 `APP_ENV` (staging/production) 环境变量隔离。
  - 前端: `EnvironmentBanner` (黄色横幅) 仅在 Staging 环境显示。
  - 数据库: 配置了独立的 `scholarflow_uat` 数据库连接 (通过 Config 类)。
- **反馈工具**: 开发了 `FeedbackWidget` (右下角悬浮按钮)，允许测试人员提交 Bug/建议。
  - 反馈数据存入 `uat_feedback` 表。
  - 管理员可在 `/admin/feedback` 页面查看反馈列表。
- **数据重置**: 开发了 `scripts/seed_staging.py` 脚本，用于一键重置 Staging 数据库并生成演示数据 (3篇特定稿件 + 1个逾期审稿任务)。
- **文档**: 创建了中文版 UAT 验收手册 `docs/UAT_SCENARIOS.md`。

### 2. 系统稳定性与安全性 ✅
- **E2E 测试**: 17/17 通过，修复了所有关键用户流测试
- **安全性**: `/editor` 路由已加入中间件保护，未授权访问会重定向到登录页
- **后端质量**: 清理了所有 Pydantic v2 deprecation 警告
- **UI 修复**: 修复了缺失的 `Badge` 组件和 `QueryProvider` 导入错误

### 3. 测试覆盖率状态 ✅
| 组件 | 覆盖率 (Lines) | 目标 | 状态 |
|------|--------|------|------|
| **后端** | **81.31%** | 80% | ✅ 达标 (280/280 测试通过) |
| **前端单元** | **73.98%** | 70% | ✅ 达标 (增加核心服务测试) |
| **前端 E2E** | **100% (17/17)** | 关键流 | ✅ 核心路径覆盖 |

### 4. 已知问题与待办
- **Pydantic 警告**: 第三方库 `pyiceberg` 仍有内部警告 (Wait for upstream fix)
- **环境**: 开发服务器需手动启动 (Playwright 不再自动启动 server)

## 🛠️ 环境配置参考

### 常用命令
```bash
# 重置 Staging 数据 (需配置 SUPABASE_SERVICE_ROLE_KEY)
cd backend && python -m scripts.seed_staging

# 后端测试
cd backend && pytest

# 前端开发服务
cd frontend && npm run dev

# E2E 测试
cd frontend && npx playwright test --project=chromium
```

### 关键路径
- **UAT 场景文档**: `docs/UAT_SCENARIOS.md`
- **UAT 组件**: `frontend/src/components/uat/`
- **种子脚本**: `backend/scripts/seed_staging.py`
- **中间件**: `/frontend/src/middleware.ts`

## 📌 后续建议

1. **部署准备** - 将 `019-uat-staging-setup` 分支部署到 Vercel (Staging) 并配置环境变量。
2. **监控 pyiceberg 更新** - 等待上游修复 Pydantic v2 警告。
3. **前端优化** - 进一步提升分支覆盖率 (当前 ~69.5%)。
