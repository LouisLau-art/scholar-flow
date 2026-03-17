# ScholarFlow 技术接手切换 Runbook

更新时间：2026-03-17  
文档状态：第二版，按现场实际切换结果修订  
目标读者：负责继续维护 ScholarFlow 的技术同事  
文档用途：在不依赖原负责人个人账号的前提下，继续让系统可运行、可验证、可排障

## 1. 这份文档只解决什么问题

这份文档不是背景介绍。

这份文档只解决三件事：

- 当前系统现在怎么继续跑
- 出问题先查哪一层
- 哪些平台已经接住，哪些还只是暂时不阻塞

## 2. 当前最重要的结论

截至 2026-03-17，本项目已经从“个人账号单点风险”切换到“接手侧可继续维护”的状态。

### 已经完成的关键动作

- Supabase：接手人已拿到当前云端项目高权限，现阶段继续复用现有项目
- Hugging Face Space：后端已从个人账号迁移到 `louis-liu-yujian` organization
- Vercel：接手侧前端部署已联通新 HF Space
- Resend：接手人已进入当前 team

### 暂时不阻塞运行的项

- Sentry 还没迁完
- Resend 仍带历史个人化域名痕迹
- 是否迁到新的公司 Supabase 项目尚未决定

## 3. 当前已验证的运行地址

以下地址为 2026-03-17 已现场验证的当前有效入口：

- 前端：`https://scholar-flow-7msj.vercel.app`
- 后端：`https://louis-liu-yujian-scholarflow-api.hf.space`

现场已验证：

- `GET https://scholar-flow-7msj.vercel.app` 返回 200
- `GET https://scholar-flow-7msj.vercel.app/api/v1/cms/menu?location=header` 返回 200
- `GET https://louis-liu-yujian-scholarflow-api.hf.space` 返回 200
- `GET https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/public/journals` 返回 200

## 4. 成功标准

对于当前接手阶段，满足以下条件即可判定“系统已被接住”：

- 接手人能登录并管理 Supabase、HF Space、Vercel、Resend
- 前端能打开并正常访问后端
- 登录后 Dashboard 不再因为后端地址错误而报 404
- 后端公开接口可用
- 邮件链路至少可继续配置和排查

Sentry 不是当前成功标准的一部分。

## 5. 当前平台状态表

| 平台 | 当前状态 | 当前用途 | 当前判断 |
| --- | --- | --- | --- |
| Supabase | 继续复用现有云端项目 `mmvulyrfsorqdpdrzbkd` | 数据库、Auth、Storage | 已接住 |
| Hugging Face Space | 已迁移到 `louis-liu-yujian` organization | 后端运行 | 已接住 |
| Vercel | 接手侧部署地址已可访问 | 前端运行 | 已接住 |
| Resend | 接手人已进当前 team | 邮件发送 | 已接住，但需后续去个人化 |
| Sentry | 未补齐 | 异常监控 | 非 blocker |

## 6. 五个平台现在分别怎么处理

## 6.1 Supabase

### 当前口径

- 不迁库
- 不重建项目
- 先继续使用当前云端项目

### 为什么

- 这是最短时间恢复系统独立运行的做法
- 当前 blocker 不是“数据库必须换新”，而是“接手人能不能继续操作当前数据库项目”

### 接手人至少要能做的事

- 进入项目后台
- 打开 SQL Editor
- 打开 Auth
- 打开 Storage
- 查看项目 URL、anon key、service role key

## 6.2 Hugging Face Space

### 当前口径

- 后端已经不再用原负责人个人 namespace
- 当前有效 backend 地址是：
  `https://louis-liu-yujian-scholarflow-api.hf.space`

### 后续接手最重要的动作

- 不要再使用旧地址 `louisshawn-scholarflow-api.hf.space`
- 修改 Variables / Secrets 后，记得重启或重新部署
- 所有前端后端联通故障，先核对前端是不是仍打到了旧 Space

## 6.3 Vercel

### 当前口径

- 前端已经能通过接手侧资源访问
- 本轮已经处理过一次典型故障：HF Space 地址变更后，Vercel rewrite 未跟着更新，导致 Dashboard 权限信息加载失败

### 最小关键环境变量

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

推荐补齐：

- `BACKEND_ORIGIN`

### 注意

- `BACKEND_ORIGIN` 不是绝对必须，但如果配置了，就必须和 `NEXT_PUBLIC_API_URL` 指向同一个后端
- 改完环境变量后必须 redeploy；只保存 env 不会让 rewrite 自动更新

## 6.4 Resend

### 当前口径

- 接手人已进入当前 team，邮件平台不再只有原负责人能登录
- 这已经满足“继续运行”的最低目标

### 但它仍不是最终完成态

- 当前 sender/domain 仍带历史个人化痕迹
- 后续最好改成公司正式域名或公司控制的发送子域名

### 当前真正依赖的变量

- `RESEND_API_KEY`
- `EMAIL_SENDER`
- `RESEND_WEBHOOK_SECRET`

这些变量在 HF Space 侧维护，不在 Vercel 里配。

## 6.5 Sentry

### 当前口径

- 当前不作为 blocker

### 什么时候再补

- 当系统已经稳定可运行
- 当需要更顺手地看线上报错和性能问题

## 7. 当前最小环境变量矩阵

## 7.1 Vercel

必需：

- `NEXT_PUBLIC_API_URL=https://louis-liu-yujian-scholarflow-api.hf.space`
- `NEXT_PUBLIC_SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=[见平台后台]`

推荐：

- `BACKEND_ORIGIN=https://louis-liu-yujian-scholarflow-api.hf.space`

说明：

- 如果 `NEXT_PUBLIC_API_URL` 是对的，`BACKEND_ORIGIN` 缺失并不一定马上阻塞
- 但一旦 rewrite 有问题，优先补 `BACKEND_ORIGIN` 并 redeploy

## 7.2 Hugging Face Space

核心必需：

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `FRONTEND_ORIGIN`
- `ADMIN_API_KEY`
- `MAGIC_LINK_JWT_SECRET`

邮件相关：

- `RESEND_API_KEY`
- `EMAIL_SENDER`
- `RESEND_WEBHOOK_SECRET`

## 8. 故障优先级

后续继续维护时，不要平均排查。按下面顺序查：

1. 地址对不对
2. 平台 env 对不对
3. 是否 redeploy / restart 生效
4. 再看业务逻辑

## 8.1 典型故障一：Dashboard 提示“当前无法加载 Dashboard 权限信息”

优先排查：

- `NEXT_PUBLIC_API_URL`
- `BACKEND_ORIGIN`
- Vercel 当前环境变量 scope 是否正确
- 是否 redeploy

判断标准：

- 如果前端域名上的 `/api/v1/*` 返回的是 Vercel HTML 404，而不是后端 JSON，那么就是 rewrite 没生效

## 8.2 典型故障二：HF 后端看起来正常，但前端全是 404

优先排查：

- 前端是否仍在打旧的 HF Space 地址
- Vercel env 是否只改了一个变量，没有同步另一个

## 8.3 典型故障三：邮件发不出去

优先排查：

- `RESEND_API_KEY`
- `EMAIL_SENDER`
- 当前 sender 是否还停留在开发发件人或历史个人化域名
- `RESEND_WEBHOOK_SECRET`

## 9. 快速验证命令

## 9.1 验证后端公开接口

```bash
curl -fsS https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/public/journals
```

## 9.2 验证前端 rewrite 是否生效

```bash
curl -fsS "https://scholar-flow-7msj.vercel.app/api/v1/cms/menu?location=header"
```

预期：返回 JSON，不是 HTML 404 页面。

## 9.3 验证运行版本

```bash
curl -H "X-Admin-Key: <管理员密钥>" \
  https://louis-liu-yujian-scholarflow-api.hf.space/api/v1/internal/runtime-version
```

## 10. 如果云端一时不稳，怎么本地继续跑

如果后续某个平台暂时出问题，但又不想立即折腾迁移，可以先本地运行前后端。

### 基本思路

- 本地前后端运行
- 继续连当前云端 Supabase
- 暂时不依赖 Vercel 与 HF 的生产链路

### 前端最小本地变量

放在 `frontend/.env.local`：

```ini
NEXT_PUBLIC_SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[见平台后台]
BACKEND_ORIGIN=http://127.0.0.1:8000
```

### 后端最小本地变量

放在 `backend/.env`：

```ini
SUPABASE_URL=https://mmvulyrfsorqdpdrzbkd.supabase.co
SUPABASE_ANON_KEY=[见平台后台]
SUPABASE_SERVICE_ROLE_KEY=[见平台后台]
FRONTEND_ORIGIN=http://localhost:3000
GO_ENV=dev
```

### 启动

```bash
./start.sh
```

## 11. 当前不该浪费时间做的事

在这轮接手里，先不要把精力花在下面这些事上：

- 立刻重做 Sentry 组织结构
- 立刻迁 Supabase 到全新项目
- 立刻重整所有平台命名
- 立刻做漂亮但无助于运行的治理文档

## 12. 继续维护时最该记住的一句话

如果线上再出“前端能打开，但数据全挂了”的问题，第一反应不是去改业务代码，而是先查：

- Vercel 当前生效的 backend 地址
- HF Space 当前真实地址
- `/api/v1/*` 到底有没有被正确转发
