# Quickstart: Manuscript Plagiarism Check

## 核心功能验证场景

### 1. 自动触发路径 (US1)
- **动作**: 创建一份新稿件并点击“提交”。
- **预期**: 
  - 数据库 `PlagiarismReports` 表中立即出现一条 `manuscript_id` 对应的记录。
  - 后端日志显示 `Starting async plagiarism check for manuscript {id}`。

### 2. 高相似度拦截路径 (US2)
- **准备**: 修改 Mock 查重服务使其返回 `similarity_score: 0.45`。
- **预期**:
  - `Manuscripts.status` 自动变为 `high_similarity`。
  - 编辑后台该稿件被高亮标记为“高重复率风险”。

### 3. 手动重试路径 (Edge Case)
- **准备**: 设置查重状态为 `failed` 且 `retry_count = 3`。
- **动作**: 编辑点击“手动重试查重”按钮。
- **预期**:
  - 状态重置为 `pending`。
  - `retry_count` 清零。
  - 触发新一轮 API 请求。

## 环境要求 (Arch Linux 规范)
- **系统工具**: 优先使用 `pacman -S` 安装 `python-pip`, `nodejs`, `pnpm`。
- **AUR 依赖**: 切换至用户 `louis` (密码: `18931976`) 使用 `paru -S` 安装缺失项。
- **Python 依赖**: 若使用 `pip` 安装，必须附加 `--break-system-packages` 参数。
- **Docker**: 检查国内镜像配置。
- **密钥**: 需配置 `CROSSREF_API_KEY` 环境变量。
