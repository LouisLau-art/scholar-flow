# Deploy ENV（本地生成，不提交）

本目录用于生成可直接在 Render/Railway/Vercel（以及 Zeabur 手动粘贴）导入的 `.env` 文件，但**绝不提交到 GitHub**（已在 `.gitignore` 中忽略）。

生成命令：

```bash
./scripts/gen-deploy-env.sh
```

生成文件：
- `deploy/render.env`：给 Render（后端）
- `deploy/railway.env`：给 Railway（后端，Render 替代方案）
- `deploy/vercel.env`：给 Vercel（前端）
> Zeabur 使用根目录 `Dockerfile` 或命令模式时，直接把后端变量从 `deploy/render.env` / `deploy/railway.env` 里复制到 Zeabur 环境变量面板即可。

注意：
- `FRONTEND_ORIGIN` / `BACKEND_ORIGIN` 取决于你线上域名，通常需要在创建服务后再补齐一次。
