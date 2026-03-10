# Open Work Items

日期：2026-03-10  
当前代码锚点：`0162528` 之后的本地收口中  
目的：把最近连续插入的新需求与遗留问题收敛成一份可执行清单，避免工作流漂移。

## 一、正在收口

### 1. 投稿作者元数据结构化

目标：

- 投稿时必须支持：
  - 投稿联系邮箱
  - 多作者列表
  - 唯一通讯作者
  - 每位作者至少包含：姓名、邮箱、机构
- 作者不要求在 ScholarFlow 中预先存在账号

当前状态：

- 前端投稿表单已支持 `submission_email + author_contacts[]`
- 后端模型、写库逻辑、远端 Supabase migration 已完成
- 稿件详情页已开始展示：
  - Authors
  - Corresponding Author
  - Submission Email
  - Special Issue

剩余收尾：

- 把其余作者侧通知邮件统一切到优先使用 `submission_email / corresponding author email`
- 继续检查作者详情、作者看板、导出/决策信中是否还在默认使用账号邮箱

## 二、高优先级未完成

### 2. 邮箱唯一性与重复用户问题

现象：

- 同一邮箱可被重复邀请/创建，导致数据库里出现两条不同用户记录但邮箱相同

风险：

- 认证、通知、权限、审稿邀请、User Management 全部会出现歧义

待做：

- 先确认重复发生在：
  - `auth.users`
  - `public.user_profiles`
  - 还是二者映射失配
- 然后补：
  - 数据清理脚本
  - 创建/邀请路径唯一性校验
  - 数据库约束或应用层保护

### 3. Academic Editor 正式模型与稿件绑定

目标：

- 引入“学术编辑”正式语义
- 同一篇稿件在 pre-check 阶段选中的学术编辑，后续默认沿用同一人
- 允许显式改派，但不是每轮随机落到其他学术编辑

当前状态：

- 目前只有 academic queue / EIC 范式，没有 per-manuscript academic assignee 模型

待做：

- 设计角色模型、稿件绑定字段、默认继承规则、改派动作

### 4. Reviewer 邀请邮件预览弹窗

目标：

- 点击 `Send Email` 后不再一键发送
- 先弹出预览：
  - 可改收件人
  - 可查看变量已渲染后的 HTML
  - 再确认发送

当前状态：

- 目前仍为模板选择后一键发送

## 三、Reviewer / Decision 仍需继续收口

### 5. reviewer history / reminder 审计细化

待做：

- `reminder by / reminder via`
- reviewer timeline 更贴近参考图
- 视需要评估独立 `review_assignment_events` 表

### 6. 邮件可信度收尾

待做：

- `DMARC`
- `custom return-path`
- 国内邮箱客户端的可信展示优化

### 7. review-stage-exit / cancel 真实链路继续观察

说明：

- 第一轮状态机已落地
- 但用户现场仍反馈过：
  - `cancel reviewer` 转圈
  - exit review stage 某些组合下未按预期推进

待做：

- 基于真实 UAT 数据继续复测和补 E2E

## 四、UI / 交互稳定性问题

### 8. date picker / popover 同类问题

当前状态：

- reviewer magic link 接受邀请页已改回原生 date input，主路径不再依赖自定义 popover date picker

待做：

- 继续梳理其他仍使用 `Popover + Calendar` 的页面
- 明确哪些场景保留原生，哪些值得重做稳定自定义组件

## 五、自动化与发布保障

### 9. UAT Canonical Smoke 继续收敛

已完成：

- HF runtime SHA gate
- Vercel frontend runtime SHA gate
- platform readiness
- linked migration parity

待做：

- 继续把 editor / reviewer / decision 的关键真实链路纳入 smoke
- 减少脆弱的 network-level wait，更多转向页面级稳定断言

## 六、建议执行顺序

1. 提交并发布投稿作者元数据这条线
2. 修邮箱唯一性问题
3. 设计并落地 academic editor 正式模型
4. 做 reviewer 邀请邮件预览弹窗
5. 继续 reviewer history / reminder / 邮件可信度收尾
