# Quickstart Guide: 超级用户管理后台

**Feature**: 017-super-admin-management
**Date**: 2026-01-31
**Purpose**: 快速开始使用和开发本功能的指南

## 快速开始

### 1. 环境准备

确保以下工具已安装并配置：

```bash
# 检查Python版本
python --version  # 需要 3.14+

# 检查Node.js版本
node --version    # 需要 20.x+

# 检查Supabase CLI
supabase --version

# 检查项目依赖
cd /home/louis/scholar-flow
pip install -r backend/requirements.txt
npm install --prefix frontend
```

### 2. 数据库迁移

运行以下命令创建本功能所需的数据库表：

```bash
cd /home/louis/scholar-flow

# 方法1: 使用Supabase迁移
supabase migration new create_user_management_tables

# 编辑生成的迁移文件，添加data-model.md中的SQL
# 然后运行迁移
supabase migration up

# 方法2: 直接执行SQL
psql -h localhost -U postgres -d scholarflow -f specs/017-super-admin-management/data-model.md
# (提取SQL部分执行)
```

### 3. 启动开发服务器

```bash
cd /home/louis/scholar-flow

# 启动后端开发服务器
cd backend
uvicorn src.main:app --reload --port 8000

# 启动前端开发服务器 (新终端)
cd frontend
npm run dev
```

访问 http://localhost:3000/admin/users 开始使用用户管理功能。

## 开发工作流

### 1. 后端开发

**API端点位置**: `backend/src/api/v1/admin/users.py`

**核心服务**: `backend/src/services/user_management.py`

**数据模型**: `backend/src/models/user_management.py`

**测试文件**: `backend/tests/unit/test_user_management.py`

**开发步骤**:
1. 在`models/user_management.py`中定义Pydantic模型
2. 在`services/user_management.py`中实现业务逻辑
3. 在`api/v1/admin/users.py`中定义API端点
4. 在`tests/unit/test_user_management.py`中编写测试

### 2. 前端开发

**页面位置**: `frontend/src/pages/admin/users/`

**组件位置**: `frontend/src/components/admin/`

**服务层**: `frontend/src/services/admin/userService.ts`

**开发步骤**:
1. 在`components/admin/`中创建可复用组件
2. 在`pages/admin/users/`中定义页面结构
3. 在`services/admin/userService.ts`中封装API调用
4. 在`tests/unit/`中编写组件测试

## 核心API使用示例

### 1. 获取用户列表

```python
# Python示例
import httpx

async def get_users(page: int = 1, per_page: int = 20):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/admin/users",
            params={"page": page, "per_page": per_page},
            headers={"Authorization": "Bearer YOUR_SUPABASE_JWT"}
        )
        return response.json()
```

```typescript
// TypeScript示例
import { userService } from '@/services/admin/userService';

// 获取第一页用户
const users = await userService.getUsers({
  page: 1,
  perPage: 20,
  search: 'example@email.com',
  role: 'editor'
});
```

### 2. 修改用户角色

```python
# Python示例
async def update_user_role(user_id: str, new_role: str, reason: str):
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"http://localhost:8000/api/v1/admin/users/{user_id}/role",
            json={"new_role": new_role, "reason": reason},
            headers={"Authorization": "Bearer YOUR_SUPABASE_JWT"}
        )
        return response.json()
```

### 3. 创建内部编辑账号

```python
# Python示例
async def create_internal_editor(email: str, name: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/admin/users",
            json={"email": email, "name": name, "role": "editor"},
            headers={"Authorization": "Bearer YOUR_SUPABASE_JWT"}
        )
        return response.json()
```

## 测试指南

### 1. 后端测试

```bash
cd /home/louis/scholar-flow/backend

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_user_management.py -v

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 2. 前端测试

```bash
cd /home/louis/scholar-flow/frontend

# 运行单元测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行E2E测试
npm run test:e2e
```

### 3. 契约测试

确保前后端API契约一致：

```bash
# 生成OpenAPI规范
cd backend
python scripts/generate_openapi.py

# 验证前端API调用与规范匹配
cd frontend
npm run validate-api-contracts
```

## 部署检查清单

### 1. 数据库检查
- [ ] 所有迁移已应用到生产数据库
- [ ] RLS策略已正确配置
- [ ] 索引已创建优化查询性能

### 2. 后端检查
- [ ] 环境变量已正确设置（SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY）
- [ ] 依赖包已安装并锁定版本
- [ ] 所有测试通过

### 3. 前端检查
- [ ] 构建成功无错误
- [ ] 环境变量已正确配置
- [ ] 路由配置正确

### 4. 安全检查
- [ ] 服务角色密钥安全存储
- [ ] 审计日志功能正常
- [ ] 角色权限验证正确

## 故障排除

### 常见问题

1. **权限错误**: 确保使用超级管理员JWT令牌
2. **分页问题**: 检查页码和每页数量参数
3. **邮件发送失败**: 检查邮件服务配置和网络连接
4. **数据库连接失败**: 验证Supabase连接配置

### 调试建议

1. 检查后端日志中的详细错误信息
2. 使用Supabase Dashboard查看数据库状态
3. 验证JWT令牌的有效性和权限
4. 检查网络请求的完整响应

## 下一步

1. **实现后端API**: 按照data-model.md设计实现服务层和API端点
2. **开发前端界面**: 创建用户管理页面和组件
3. **编写测试**: 确保功能稳定可靠
4. **集成测试**: 验证前后端协作正常

如需帮助，请参考项目文档或联系开发团队。