# DevOps Hardening Checklist

更新时间：2026-02-26

## 已落地（仓库内）

1. `deploy-hf` 仅在 `ScholarFlow CI` 成功后触发（并保留手动触发）。
2. CI 增加最小权限与并发控制，前端依赖安装改为 `--frozen-lockfile`。
3. 新增 Dependabot（GitHub Actions / backend pip / frontend npm）。
4. 新增每周安全审计 workflow（`pip-audit` + `bun audit`）。
5. Docker 镜像补充 `HEALTHCHECK`。

## 仍需在平台侧手工完成

1. 打开 `main` 分支保护（Branch protection）：
   - Require a pull request before merging
   - Require approvals（建议 1+）
   - Require status checks to pass before merging
   - Required checks 至少包含：
     - `backend-ci`
     - `frontend-ci`
2. 限制直接 push 到 `main`（仅允许管理员紧急放行）。
3. 在 GitHub Settings > Secrets and variables 完成轮换：
   - `HF_TOKEN`
   - Sentry token
   - 所有后端密钥（若曾在本地/历史脚本中明文出现）
4. 在 Hugging Face / Vercel 平台开启部署失败告警通知（邮件/Slack）。

## 建议的每周巡检

1. 查看 `Security Audit` workflow 结果并处理高危漏洞。
2. 查看 Dependabot PR，优先处理安全更新。
3. 抽查最近一次生产部署：
   - 是否由 CI 成功触发
   - 是否对应正确 commit SHA
