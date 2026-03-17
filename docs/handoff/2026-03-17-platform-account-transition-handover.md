# ScholarFlow 平台账号与离职交接文档

更新时间：2026-03-17  
文档状态：第二版，已按现场实际迁移结果修订  
适用对象：管理侧、技术接手人、后续运维支持方  
文档用途：说明五个平台当前已交接到哪一步、哪些风险已解除、哪些仍然存在但暂时不是 blocker

## 1. 文档目的

本文件不是产品介绍，也不是研发总结。

本文件只回答四个问题：

- 离职后系统现在还能不能继续跑
- 哪些第三方平台已经脱离原负责人个人账号依赖
- 哪些平台只是“先接住了”，但还没有彻底公司化
- 后续如果继续迁移，优先级应该怎么排

## 2. 交接边界

本文覆盖以下五个平台：

- Supabase：数据库、认证、存储
- Hugging Face Space：后端运行环境
- Vercel：前端运行环境
- Resend：事务邮件发送与回调
- Sentry：异常监控与告警

本文不记录：

- 任意密钥明文
- 任意个人密码
- MFA 验证码
- 公网代码托管信息

## 3. 当前总判断

截至 2026-03-17，本次交接已经从“高风险单点依赖”推进到“系统可继续运行，但仍有后续收尾项”。

### 3.1 已经解除的主要风险

- Supabase 不再只有原负责人能进入和管理
- Hugging Face Space 已脱离原负责人个人 namespace
- Vercel 前端已由接手侧资源承接并能访问正确后端
- Resend 已不再只有原负责人可进入后台

### 3.2 仍然存在但暂时不是 blocker 的风险

- Sentry 尚未迁完
- Resend 发信域名仍存在历史个人化痕迹，后续应替换为公司域名或公司子域名
- 当前继续复用原 Supabase 云端项目，是否迁到全新公司项目尚未决定

## 4. 当前状态快照

以下内容基于 2026-03-17 现场核验结果整理。

| 平台 | 当前状态 | 是否已脱离原负责人个人账号单点 | 当前判断 |
| --- | --- | --- | --- |
| Supabase | 接手人已获得当前项目管理权限，系统继续复用现有云端项目 `mmvulyrfsorqdpdrzbkd` | 是 | 已接住 |
| Hugging Face Space | Space 已从原负责人个人账号迁移至 `louis-liu-yujian` organization；新运行地址已验证可用 | 是 | 已接住 |
| Vercel | 接手侧前端部署已可访问，且 `/api/v1/*` 已正确转发到新 HF Space | 是 | 已接住 |
| Resend | 接手人已进入当前 team，可继续管理发信域名、API Key、Webhook | 基本是 | 已接住，但未彻底去个人化 |
| Sentry | 尚未完成迁移或补齐接手人权限 | 否 | 非 blocker，待后续处理 |

## 5. 当前已验证的运行入口

以下入口为现场已验证可用的当前运行面：

- 当前接手侧前端地址：`https://scholar-flow-7msj.vercel.app`
- 当前后端地址：`https://louis-liu-yujian-scholarflow-api.hf.space`
- 后端公开接口：`GET /api/v1/public/journals` 返回 200
- 前端经 Vercel rewrite 的接口：`GET /api/v1/cms/menu?location=header` 返回 200

说明：

- 仓库中部分旧模板仍保留历史 HF Space 地址，仅可作字段名参考，不能再作为最新地址来源。
- 当前一切以平台后台生效配置和上述现场已验证地址为准。

## 6. 平台逐项交接结果

## 6.1 Supabase

### 当前结果

- 接手人已拿到当前项目的高权限访问能力
- 当前系统继续使用现有云端 Supabase 项目
- 本轮未强制进行“新建公司名下 Supabase 项目并迁库”

### 这意味着什么

- 数据库、Auth、Storage 这条主链路现在可以继续跑
- 本轮目标是先消除“只有原负责人能操作”的风险
- 是否整体迁往新项目，留给后续单独决策

### 剩余风险

- 现有项目是否最终视为“公司正式资产”还需管理口径确认
- 如未来迁往新项目，需要单独迁数据库、Auth、Storage 与环境变量

## 6.2 Hugging Face Space

### 当前结果

- 原 Space 已从原负责人个人账号迁移到 `louis-liu-yujian` organization
- 新运行地址为 `https://louis-liu-yujian-scholarflow-api.hf.space`
- 现场验证：
  - 根地址返回 200
  - `GET /api/v1/public/journals` 返回 200

### 这意味着什么

- 后端运行资源已不再绑在原负责人个人 namespace 下
- 前端已需要统一指向新的 HF Space 地址

### 剩余风险

- 仓库内历史模板和部分旧文档仍可能出现旧地址 `louisshawn-scholarflow-api.hf.space`
- 后续任何接手人都不应再把旧地址当成有效 backend origin

## 6.3 Vercel

### 当前结果

- 接手侧前端部署已可访问：`https://scholar-flow-7msj.vercel.app`
- 现场验证 Vercel 上的 `/api/v1/*` 已成功转发至新 HF Space
- 本轮已处理过一次典型故障：HF Space 地址变更后，Vercel 因环境变量未同步而出现 Dashboard 404/权限信息加载失败；调整环境变量并 redeploy 后已恢复

### 当前最小关键变量

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `BACKEND_ORIGIN` 推荐与 `NEXT_PUBLIC_API_URL` 保持一致

### 剩余风险

- 如果后续再改 HF Space 地址，必须同时检查 `NEXT_PUBLIC_API_URL` 与 `BACKEND_ORIGIN`
- 如果只是改环境变量不 redeploy，rewrite 仍会继续使用旧值

## 6.4 Resend

### 当前结果

- 接手人已进入当前 Resend team
- 当前邮件链路因此不再只有原负责人能登录后台

### 当前判断

- 对“系统继续跑”这个目标来说，Resend 已基本接住
- 但对“彻底去个人化”这个目标来说，Resend 仍未收尾

### 剩余风险

- 当前发信域名仍带有历史个人化痕迹
- 后续建议改为公司正式域名或公司控制的发送子域名
- 同时应重建或轮换：
  - `RESEND_API_KEY`
  - `EMAIL_SENDER`
  - `RESEND_WEBHOOK_SECRET`

## 6.5 Sentry

### 当前结果

- 本轮未作为必须完成项

### 当前判断

- 对“系统能继续跑”来说，Sentry 不是 blocker
- 对“后续运维效率与异常排查”来说，Sentry 仍值得补齐

### 后续建议

- 至少把接手人加进当前 Sentry organization
- 最低目标是让接手人能查看异常、管理告警和自测事件

## 7. 当前 blocker 与 non-blocker 划分

### 7.1 当前 blocker

- 当前前端无法访问
- 前端无法再打到正确后端
- Supabase 当前项目无人可管理
- HF Space 当前资源无人可管理
- Resend 当前团队无人可管理

### 7.2 当前 non-blocker

- Sentry 尚未完成迁移
- 是否立即把 Supabase 迁到全新公司项目
- 是否立即把 Resend 的历史个人化域名替换干净
- 是否立即统一所有平台命名与组织结构

## 8. 技术上当前最重要的事实

后续任何人继续接手时，都要优先记住下面几条：

- 当前系统继续依赖现有云端 Supabase 项目，而不是本地数据库
- 当前 HF Space 新地址已经改变，旧地址不可再用
- Vercel 与 HF 的联通问题，优先先查 `NEXT_PUBLIC_API_URL` 和 `BACKEND_ORIGIN`
- 当前 Resend 虽已接住，但仍应视为“可运行的过渡态”
- Sentry 可暂缓，不影响系统继续运行

## 9. 建议的后续收尾顺序

如果离职窗口之后还有时间，建议按下面顺序继续完善：

1. 补齐 Sentry 接手权限
2. 把 Resend 发信域名替换为公司控制域名
3. 决定是否迁移到新的公司 Supabase 项目
4. 清理仓库里残留的旧平台地址与旧模板

## 10. 本文对应的执行文档

如果需要继续具体执行，不要只看本文，继续看下面两份：

- 技术同事执行版：`2026-03-17-technical-successor-cutover-runbook.md`
- AI / Agent 消费版：`2026-03-17-ai-operator-context-pack.md`
