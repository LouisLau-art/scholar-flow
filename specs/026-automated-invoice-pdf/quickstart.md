# Quickstart: Automated Invoice PDF (Feature 026)

本 Quickstart 目标：让你在本地/云端环境里验证“录用后自动生成账单 PDF，并可下载”。

## 1) 数据库与 Storage 准备（云端 Supabase）

### 1.1 应用数据库迁移

- 优先使用 Supabase CLI：`supabase db push --linked`
- 若 CLI 不可用：到 Supabase Dashboard → SQL Editor 执行本 feature 对应 migration（实现阶段会新增）。

### 1.2 创建 Storage Bucket：`invoices`

**建议**：私有桶（`public=false`），下载走后端 `signed_url`。

可在 Dashboard → Storage → Buckets 手动创建：
- Name: `invoices`
- Public: `false`

## 2) 后端环境变量（示例）

实现阶段会新增/复用以下配置（名称以实现为准）：

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`（仅后端）
- `INVOICE_PAYMENT_INSTRUCTIONS`（银行信息/收款信息，英文多行文本）

## 3) 本地验证流程（MVP）

1. Author 提交稿件 → Editor 完成外审 → 在 Decision 中点击 Accept（进入 `approved`）
2. 确认 `invoices` 表存在该稿件对应记录（`manuscript_id UNIQUE`）
3. 系统自动生成 invoice PDF 并上传到 Storage `invoices`（后台任务完成后回填 `invoices.pdf_path`）
4. Author/Editor 在 UI 点击 “Download Invoice”
   - 前端调用 `GET /api/v1/invoices/{invoice_id}/pdf-signed`
   - 浏览器打开/下载返回的 `signed_url`

## 4) 故障排查

- 下载返回 404：通常是 invoice 记录存在但 `pdf_path` 为空（生成失败/尚未完成）。
- 生成失败：检查后端日志中 WeasyPrint 相关错误；容器环境通常缺少 Cairo/Pango/字体依赖。
- 权限 403：确认当前用户是该稿件作者或拥有 `editor/admin` 角色；并确认后端未把 signed URL 下发给未授权用户。

