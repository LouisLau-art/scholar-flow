# Quickstart: ScholarFlow Core Workflow

## 核心业务链路验证

### 1. 投稿解析与回退 (US1)
- **验证**: 上传损坏或格式异常的 PDF。
- **期望**: 系统检测到解析失败，前端展示手动填写表单，作者能正常完成投稿。

### 2. 质检与退回 (US2)
- **验证**: 编辑选择“退回修改”，状态变更为 `returned_for_revision`。
- **期望**: 作者在首页能看到退回状态，并支持修改后再次提交。

### 3. 免登录审稿 (US3)
- **验证**: 使用过期的 Token (修改数据库 expiry_date) 访问页面。
- **期望**: 前端提示“Token 已过期”，无法预览 PDF 或提交报告。

### 4. 财务上线锁 (US4)
- **验证**: 在 `Invoices.status = 'unpaid'` 时，尝试通过 API 或按钮将稿件设为 `published`。
- **期望**: 后端返回 403 错误，逻辑拦截生效。

### 5. AI 邀请逻辑 (US5)
- **验证**: 编辑点击“邀请”按钮。
- **期望**: 后端生成 Token，创建状态为 `invited` 的 ReviewReport，并触发发送邮件。

## 环境要求 (Arch Linux 规范)
- **系统工具**: 优先使用 `pacman -S` 安装 `python-pip`, `nodejs`, `pnpm`。
- **AUR 依赖**: 切换至用户 `louis` (密码: `18931976`) 使用 `paru -S` 安装缺失项。
- **Python 依赖**: 若使用 `pip` 安装，必须附加 `--break-system-packages` 参数。
- **前端环境**: 优先使用 `pnpm` 管理依赖。
- **Docker**: 检查 `/etc/docker/daemon.json` 是否配置国内镜像。
- **环境变量**: 需配置 `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`。
