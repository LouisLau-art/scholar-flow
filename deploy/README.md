# Deploy ENV（本地生成，不提交）

本目录用于生成可直接在 Render/Vercel 导入的 `.env` 文件，但**绝不提交到 GitHub**（已在 `.gitignore` 中忽略）。

生成命令：

```bash
./scripts/gen-deploy-env.sh
```

生成文件：
- `deploy/render.env`：给 Render（后端）
- `deploy/railway.env`：给 Railway（后端，Render 替代方案）
- `deploy/vercel.env`：给 Vercel（前端）

注意：
- `FRONTEND_ORIGIN` / `BACKEND_ORIGIN` 取决于你线上域名，通常需要在创建服务后再补齐一次。
