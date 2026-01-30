# Feature 015: Academic Indexing & DOI Minting - Requirements Checklist

## DOI 注册 (P1)

### 后端实现
- [ ] 创建 `DOIRegistration` 数据模型 (Pydantic v2)
- [ ] 创建 `DOITask` 任务队列模型
- [ ] 实现 Crossref API 客户端 (`backend/app/services/crossref_client.py`)
  - [ ] 元数据 XML 生成 (Crossref Schema 4.8+)
  - [ ] Deposit API 调用
  - [ ] 响应解析与错误处理
- [ ] 实现 DOI 服务层 (`backend/app/services/doi_service.py`)
  - [ ] `register_doi()` - 注册新 DOI
  - [ ] `update_doi()` - 更新 DOI 元数据
  - [ ] `get_doi_status()` - 查询注册状态
- [ ] 实现异步任务队列 (`backend/app/core/doi_worker.py`)
  - [ ] 任务调度
  - [ ] 指数退避重试 (1min, 5min, 30min, 2h)
  - [ ] 失败通知
- [ ] 创建 DOI API 端点 (`backend/app/api/v1/doi.py`)
  - [ ] POST `/api/v1/doi/register` - 触发注册
  - [ ] GET `/api/v1/doi/{article_id}` - 查询状态
  - [ ] POST `/api/v1/doi/{article_id}/retry` - 手动重试

### 数据库迁移
- [ ] 创建 `doi_registrations` 表
- [ ] 创建 `doi_tasks` 队列表
- [ ] 添加 `articles.doi` 字段（如不存在）

### 测试
- [ ] 单元测试: Crossref XML 生成
- [ ] 单元测试: 重试逻辑
- [ ] 集成测试: Crossref API 调用 (Mock)
- [ ] 集成测试: 完整注册流程

---

## Google Scholar 适配 (P2)

### 前端实现
- [ ] 创建 Highwire Press Meta Tags 生成函数 (`frontend/src/lib/metadata/citation.ts`)
- [ ] 实现文章详情页 `generateMetadata` (SSR)
  - [ ] citation_title
  - [ ] citation_author (多作者支持)
  - [ ] citation_publication_date
  - [ ] citation_journal_title
  - [ ] citation_doi
  - [ ] citation_pdf_url
  - [ ] citation_abstract
  - [ ] citation_volume / citation_issue
  - [ ] citation_firstpage / citation_lastpage
- [ ] 处理作者姓名格式 (中英文)

### 测试
- [ ] 单元测试: Meta Tags 生成
- [ ] E2E 测试: 页面包含正确标签

---

## OAI-PMH 接口 (P3)

### 后端实现
- [ ] 实现 OAI-PMH 核心模块 (`backend/app/services/oaipmh/`)
  - [ ] `protocol.py` - 协议处理
  - [ ] `dublin_core.py` - Dublin Core 映射
  - [ ] `resumption.py` - 分页 Token 管理
- [ ] 实现 6 个标准动词:
  - [ ] `Identify` - 仓储信息
  - [ ] `ListMetadataFormats` - 支持的元数据格式
  - [ ] `ListSets` - 集合列表 (可选)
  - [ ] `ListIdentifiers` - 标识符列表
  - [ ] `ListRecords` - 记录列表
  - [ ] `GetRecord` - 单条记录
- [ ] 实现日期范围过滤 (`from`, `until`)
- [ ] 实现分页机制 (每页 100 条)
- [ ] 创建 OAI-PMH 端点 (`backend/app/api/v1/oaipmh.py`)
  - [ ] GET `/api/oai-pmh` - 统一入口

### 测试
- [ ] 单元测试: Dublin Core XML 生成
- [ ] 单元测试: resumptionToken 编解码
- [ ] 集成测试: 各动词响应格式
- [ ] 兼容性测试: OAI-PMH Validator

---

## 失败处理与日志 (P4)

### 后端实现
- [ ] 实现结构化日志 (`backend/app/core/doi_logger.py`)
  - [ ] 请求参数记录
  - [ ] 响应状态记录
  - [ ] 错误详情记录
- [ ] 实现邮件通知服务
  - [ ] 失败通知模板
  - [ ] 管理员邮箱配置
- [ ] 管理界面 API
  - [ ] GET `/api/v1/doi/tasks` - 任务列表
  - [ ] GET `/api/v1/doi/tasks/failed` - 失败任务

### 前端实现
- [ ] DOI 任务管理页面 (`/editor/doi-tasks`)
  - [ ] 任务列表表格
  - [ ] 状态筛选
  - [ ] 重试按钮
  - [ ] 错误详情查看

### 测试
- [ ] 单元测试: 日志格式
- [ ] 集成测试: 失败重试流程
- [ ] E2E 测试: 管理界面操作

---

## 配置与环境变量

- [ ] `CROSSREF_DEPOSITOR_EMAIL` - 存款人邮箱
- [ ] `CROSSREF_DEPOSITOR_PASSWORD` - 存款人密码
- [ ] `CROSSREF_DOI_PREFIX` - DOI 前缀 (如 `10.12345`)
- [ ] `CROSSREF_API_URL` - API 地址 (测试/生产)
- [ ] `JOURNAL_TITLE` - 期刊名称
- [ ] `JOURNAL_ISSN` - 期刊 ISSN

---

## 验收标准

- [ ] DOI 注册成功率 >= 99%
- [ ] DOI 注册耗时 < 5 分钟（正常情况）
- [ ] OAI-PMH 响应时间 < 2 秒
- [ ] Google Scholar 标签通过验证
- [ ] 失败任务 24 小时内处理
- [ ] 完整审计日志

---

## 文档

- [ ] API 文档更新 (OpenAPI)
- [ ] 配置说明文档
- [ ] Crossref 账号申请指南
