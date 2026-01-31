# ScholarFlow 项目交接文档 (2026-01-31 更新)

本文件旨在为后续接手的 AI 助手提供当前项目的完整状态上下文。

## 🚀 最新进展

### 1. 系统稳定性与安全性 ✅ (本次完成)
- **E2E 测试**: 17/17 通过，修复了所有关键用户流测试
- **安全性**: `/editor` 路由已加入中间件保护，未授权访问会重定向到登录页
- **后端质量**: 清理了所有 Pydantic v2 deprecation 警告（`@field_validator`, `ConfigDict` 等）
- **UI 修复**: 修复了缺失的 `Badge` 组件和 `QueryProvider` 导入错误

### 2. 测试覆盖率状态 ✅
| 组件 | 覆盖率 (Lines) | 目标 | 状态 |
|------|--------|------|------|
| **后端** | **81.31%** | 80% | ✅ 达标 (280/280 测试通过) |
| **前端单元** | **73.98%** | 70% | ✅ 达标 (增加核心服务测试) |
| **前端 E2E** | **100% (17/17)** | 关键流 | ✅ 核心路径覆盖 |

### 3. 已知问题与待办
- **Pydantic 警告**: 第三方库 `pyiceberg` 仍有内部警告 (Wait for upstream fix)
- **环境**: 开发服务器需手动启动 (Playwright 不再自动启动 server)

### 4. 数据库架构 (Feature 018)
- **字段对齐**: 统一使用 `full_name` 和 `affiliation`
- **数据类型**: `research_interests` 为 `text[]`
- **性能**: GIN 全文检索索引已启用

## 🛠️ 环境配置参考

### 常用命令
```bash
# 后端测试（含覆盖率）
cd backend && pytest

# 后端服务启动
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# 前端开发服务
cd frontend && npm run dev

# E2E 测试
cd frontend && npx playwright test --project=chromium

# 前端单元测试（含覆盖率）
cd frontend && npm run test:coverage
```

### 关键路径
- **中间件**: `/frontend/src/middleware.ts` (定义受保护路由)
- **E2E 测试**: `/frontend/tests/e2e/`
- **后端模型**: `/backend/app/models/` (Pydantic v2 风格)

## 📌 后续建议

1. **监控 pyiceberg 更新** - 等待上游修复 Pydantic v2 警告
2. **部署准备** - 当前 CI/CD 流程已稳定，可考虑预生产部署验证
3. **前端优化** - 进一步提升分支覆盖率 (当前 ~69.5%)
