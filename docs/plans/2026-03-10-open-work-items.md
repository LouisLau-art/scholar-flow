# Open Work Items

日期：2026-03-10  
当前代码锚点：`2a1d2ad` 之后的本地收口中
目的：把最近连续插入的新需求与遗留问题收敛成一份可执行清单，避免工作流漂移。

## 一、正在收口

### 1. 投稿作者元数据结构化

目标：

- 投稿时必须支持：
  - 投稿联系邮箱
  - 多作者列表
  - 一个或多个通讯作者
  - 每位作者至少包含：姓名、邮箱、机构
- 作者不要求在 ScholarFlow 中预先存在账号

当前状态：

- 前端投稿表单已支持 `submission_email + author_contacts[]`
- 投稿文件入口已切到：
  - `PDF + Cover Letter + (Word xor ZIP)`
  - `LaTeX` 当前只支持 `.zip`
  - ZIP 仅进入 Storage / manuscript_files，不参与 AI 解析
- 投稿页交互也已收成：
  - 先选 `Manuscript Source`
  - 再只显示单一 `Word` 或 `ZIP` 上传入口
  - 切换 source type 时要求确认并清空当前 source 文件
- 前端已补作者邮箱重复 warning，会直接提示归一化后的重复邮箱
- 移除已上传 Word 稿或切换 away 时，会清理未被手动触碰的 DOCX 派生元数据，避免旧解析结果残留
- 作者顺序已支持前端调整（`Move Up / Move Down`）
- 后端模型、写库逻辑、远端 Supabase migration 已完成
- 通讯作者现在已放宽为“至少一个，可多个”
- 每位作者已支持：
  - `affiliation`
  - `city`
  - `country_or_region`
- 稿件详情页已开始展示：
  - Authors
  - Corresponding Author(s)
  - Submission Email
  - Special Issue
- 作者侧关键邮件入口已完成统一：
  - 技术退回
  - 修回请求
  - 最终决定
  - 发票邮件
  - 发表通知
  现在全部优先使用 `submission_email / corresponding author email`
- 投稿确认邮件（Submission Received）也已统一走相同收件人解析逻辑

剩余收尾：

- 继续检查作者详情、作者看板、导出/决策信中是否还在默认使用账号邮箱

### 1.1 Reviewer Dashboard 个人历史归档

当前状态：

- 已完成

结果：

- Reviewer dashboard 现在同时展示：
  - 当前活跃审稿任务
  - 自己的历史归档（`submitted / declined / cancelled`）
- 历史详情弹窗可查看：
  - 稿件标题与摘要
  - 自己提交给作者的评论
  - 只给编辑的 confidential note
  - 自己 assignment 的 communication timeline
- 已提交历史项支持通过 session bridge 重新进入只读 reviewer workspace

边界：

- 仅展示 reviewer 自己的记录
- 不暴露其他 reviewer、编辑内部备注或内部决策流

### 1.2 Production SOP 收口

当前状态：

- 本轮已完成

结果：

- production 详细流程已收口到 `production workspace + production_cycles.stage/status`
- 稿件详情页不再直接承担 production 推进或发布动作
- 最终发布只允许：
  - `approved_for_publish -> published`
- publish 前仍必须通过：
  - payment gate
  - production publish gate
- production 相关 schema 缺失现在统一返回：
  - `503 + Production SOP schema not migrated: ...`
- linked Supabase 缺失的 production / email envelope migrations 已推到云端
- post-migration 残余问题已收口：
  - author feedback multipart 支持仅上传带批注 PDF
  - 审计日志保留 `approved_for_publish` 等 SOP 扩展状态
  - production integration tests 的 `user_profiles` seed 已按邮箱可重入
- 当前定向 backend 回归结果：
  - `69 passed`

后续仅保留：

- 做真实 UAT，再确认 production workspace 的 stage/action 文案是否还需要继续压缩
- 若后面扩展 production 前端交互，继续保持单入口，不要把 direct publish / legacy next action 放回 detail 页

## 二、高优先级未完成

### 2. 邮箱唯一性与重复用户问题

当前状态：

- 已修复

结果：

- `user_profiles.email` 已建立归一化唯一约束
- Admin invite / internal user create / reviewer library / profile fallback insert 已统一做 email normalize
- 云端重复邮箱已清零

后续仅保留：

- 若业务确认不再需要这些历史 orphan profile，可补一条安全清理脚本，处理已被改写为 `@example.invalid` 的占位邮箱记录

### 3. Academic Editor 正式模型与稿件绑定

目标：

- 引入“学术编辑”正式语义
- 同一篇稿件在 pre-check 阶段选中的学术编辑，后续默认沿用同一人
- 允许显式改派，但不是每轮随机落到其他学术编辑

当前状态：

- 第一阶段已完成，第二阶段已完成核心路径：
  - 新增正式角色 `academic_editor`
  - `journal_role_scopes` 已支持 `academic_editor`
  - `manuscripts` 已落地：
    - `academic_editor_id`
    - `academic_submitted_at`
    - `academic_completed_at`
  - AE 在 `送 Academic 预审` 时必须指定具体学术编辑
  - academic queue / detail / decision access 已开始基于真实 assignee 工作
  - 稿件详情页已支持显式改派 `Academic Editor`
  - 绑定校验已收紧：
    - 仅允许具备 `academic_editor / editor_in_chief` 且匹配期刊 scope 的用户
    - 纯 `assistant_editor` 不能查看非本人稿件的 academic 候选列表
    - 非绑定学术编辑不能代替当前 academic assignee 提交 academic check

待做：

- 收尾项：
  - 再核一轮 `first decision / academic` 默认沿用同一 academic assignee 的真实 UAT 链路

### 4. Reviewer 邀请邮件预览弹窗

目标：

- 点击 `Send Email` 后不再一键发送
- 先弹出预览：
  - 可改收件人
  - 可查看变量已渲染后的 HTML
  - 再确认发送

当前状态：

- 已完成：
  - 发送前先预览
  - 支持改收件人
  - 支持查看变量已渲染后的 HTML
  - reviewer email preview 已改成 compose-only：
    - `Subject` 可编辑
    - `HTML Body` 可编辑
    - `Plain Text` 由当前 HTML 自动派生，只读
  - override 收件人时按 preview/test-send 处理，不推进 reviewer 状态机
  - sending / saving 期间会锁定 compose dialog 与 invoice modal 关键输入，避免半提交状态

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
- 继续按最新业务口径扩展：
  - AE 可在 `under_review` 阶段直接给出 `major/minor`
  - AE 不可直接 `reject`，但可 `send_first_decision`
  - `send_first_decision` 的接收邮箱默认主编/编委，但允许改成 AE 自己（已完成 payload 持久化、Decision Workspace 展示与发信结果回传；后续主要补 smoke）
  - 作者在进入下一阶段后仍应能看到后续新到达的审稿意见（已由 author-context 集成测试锁定）
  - decision author notification 已切到 email-first，并会优先复用最近一条 workflow bucket 一致的 academic recommendation 模板；对应 route 级 smoke 已补到 `backend/tests/integration/test_decision_workspace.py`，后续主要剩 admin 模板运营化与更高层 rollout 集成

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
  - 已补最小 route 级 smoke：
    - `academic recommendation -> editorial execute(decision)` 审计链路
    - `academic recommendation -> editorial execute(under_review)` 审计链路
    - `review-stage-exit -> first decision request email` 链路
    - `final decision -> author email-first template key` 链路
  - 已补最小前端 mocked Playwright smoke：
    - `decision workspace execute mode`
    - `decision workspace recommendation-only mode`
    - `reviewer reselection explicit reuse`
  - 已补可选真实环境 smoke：
    - `deployed_smoke.spec.ts` 支持 `SMOKE_DECISION_MANUSCRIPT_ID`
- 减少脆弱的 network-level wait，更多转向页面级稳定断言

## 六、建议执行顺序

1. 跑一轮 `academic editor -> first decision` 真实 UAT，确认默认 assignee 沿用
2. 继续收口 `under_review -> send_first_decision / direct revision`
3. 继续 reviewer history / reminder / 邮件可信度收尾
4. 继续把 decision / academic / review-stage-exit 关键真实链路纳入 smoke
   当前已补 `pre_check/academic -> {under_review, decision}`、`review-stage-exit -> first decision request email`、`final decision -> author email-first template key` 四条最小 route 级 smoke，下一步优先补更高层 rollout script / UI smoke
5. 继续检查作者详情、作者看板、导出/决策信中的作者邮箱口径
