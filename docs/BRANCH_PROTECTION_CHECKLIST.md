# Branch Protection Checklist

适用仓库：`LouisLau-art/scholar-flow`  
目标分支：`main`

## 目标策略

1. 保留 GitHub CI 作为质量门禁（代码层面）。
2. 保留 Vercel 作为部署门禁（平台构建与发布层面）。
3. 避免重复构建：`frontend-ci` 的 `build` 仅在 PR 触发，`push main` 依赖 Vercel 构建。

## 必开项

1. `Require a pull request before merging`
2. `Require status checks to pass before merging`
3. `Require branches to be up to date before merging`（strict）
4. `Require linear history`
5. `Do not allow bypassing the above settings`（包含 admin）
6. `Do not allow force pushes`

## Required checks（建议）

1. `backend-ci`
2. `frontend-ci`
3. `Vercel`（若你希望部署失败也阻止合并）

## 一键查看当前保护配置

```bash
gh api repos/LouisLau-art/scholar-flow/branches/main/protection
```

## 一键更新（示例）

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  repos/LouisLau-art/scholar-flow/branches/main/protection \
  -f required_status_checks.strict=true \
  -f enforce_admins=true \
  -F required_status_checks.contexts[]="backend-ci" \
  -F required_status_checks.contexts[]="frontend-ci" \
  -F required_status_checks.contexts[]="Vercel" \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f block_creations=false \
  -f required_conversation_resolution=true
```

> 如果你暂时不想把 Vercel 设为强制门禁，删除上面 `contexts[]="Vercel"` 那行即可。
