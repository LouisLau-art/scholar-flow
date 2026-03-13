# 当前系统已实现业务流程说明（给验收方）

更新时间：2026-03-13

本文档只描述**当前系统已经落代码并可运行的真实流程**，不描述理想方案，也不描述尚未实现的规划项。  
目的：

- 让验收方明确当前系统“实际上怎么跑”
- 区分“当前已实现流程”和“后续建议优化点”
- 避免按口头理解验收，导致预期与系统现状错位

## 1. 总体原则

当前 ScholarFlow 的编辑流程主线分为五段：

1. 作者投稿
2. ME 入口分配
3. AE 技术检查
4. 外审 / 学术预审分流
5. 决策阶段

系统当前已经支持：

- 作者投稿与修回
- ME 分配 AE
- AE 直接发起外审
- AE 送学术编辑预审
- Reviewer 邀请、接受、拒绝、提交
- AE 在外审阶段直接给大修/小修，或送 first/final decision

## 2. 作者投稿阶段

### 2.1 文件要求

作者首次投稿时，当前系统现在要求上传：

1. Cover Letter
2. Word Manuscript 或 LaTeX Source ZIP（二选一）
3. Manuscript PDF

当前页面顺序也是：

1. Cover Letter
2. Manuscript Source 选择器
3. 根据选择显示：
   - Word manuscript
   - 或 LaTeX ZIP
4. PDF

当前约束：

- `PDF manuscript` 必传
- `Cover letter` 必传
- `Word manuscript` 与 `LaTeX source ZIP` 互斥二选一
- UI 先要求作者选择 `Manuscript Source`
- 未选择 source type 前，不显示 Word/ZIP 上传卡片
- 若已上传一种 source，再切换到另一种时，会先弹确认并清空当前 source 文件
- 当前只支持 `.zip`
- ZIP 仅存储给编辑部使用，不参与 AI / 大模型元数据解析

### 2.2 元数据自动解析

当前系统已切换为：

- **DOCX-first**
- **PDF-fallback**

即：

- Word 稿成功解析出标题/摘要/作者信息后，Word 成为主元数据来源
- PDF 仍为必传文件，但不再与 Word 竞争元数据主来源
- 若作者走 LaTeX ZIP 路线，则 ZIP 不参与解析，只保留 PDF 解析或作者手填

### 2.3 作者信息

当前投稿页支持填写多位作者，每位作者包含：

- 姓名
- 邮箱
- 机构
- 城市
- 国家/地区
- 是否为通讯作者

当前规则：

- 通讯作者**至少 1 位**
- 允许**多位**通讯作者
- 作者顺序可手动调整

### 2.4 投稿联系邮箱

系统支持独立的 `submission_email`，其含义是：

- 投稿联系邮箱
- 不要求等于任一作者邮箱
- 可用于学生/助理代投场景

### 2.5 作者修回后的当前回流

作者提交修回后，当前系统分两类处理：

1. `pre-check` 技术退回修回

- 若来源是 `intake`，回到 `pre_check / intake`
- 若来源是 `technical`，回到 `pre_check / technical`

2. 编辑部 `major_revision / minor_revision` 修回

- 稿件进入 `status = resubmitted`
- `version + 1`
- 会记录：
  - `latest_author_resubmitted_at`

当前系统**不会**因为上一轮是 `major_revision` 就自动创建下一轮 reviewer assignment。

也就是说：

- 系统不再自动把上一轮 reviewer 复制到新 round
- 是否再次进入 `under_review`
- 以及下一轮发给哪些 reviewer

都由编辑部后续手动决定

## 3. ME 入口阶段

### 3.1 稿件初始状态

投稿成功后，稿件进入：

- `status = pre_check`
- `pre_check_status = technical`

### 3.2 ME 可执行动作

Managing Editor 在 Intake Queue 中可执行：

1. 分配 Assistant Editor
2. 技术退回作者

分配 AE 后，稿件仍保持：

- `status = pre_check`
- `pre_check_status = technical`

只是增加：

- `assistant_editor_id`
- `ae_sla_started_at`

## 4. AE 技术检查阶段

Assistant Editor 在技术检查阶段，当前系统支持三个出口：

### 4.1 Pass

含义：

- 技术检查通过
- 直接进入外审

结果：

- `status -> under_review`
- `pre_check_status -> null`

### 4.2 Academic

含义：

- 技术层面没有问题
- 但 AE 希望先由学术编辑 / 主编做一轮外审前学术把关

结果：

- `status = pre_check`
- `pre_check_status = academic`
- 必须绑定具体：
  - `academic_editor_id`

### 4.3 Revision

含义：

- 技术层面退回作者修改

结果：

- `status -> revision_before_review`
- 当前不会继续停留在 `pre_check / technical`
- 作者修回后：
  - 若来源是 `technical`，则回到 `pre_check / technical`
  - 若来源是 `intake`，则回到 `pre_check / intake`

当前系统还会同步记录：

- `latest_author_resubmitted_at`
- `ae_sla_started_at`（仅在重新回到 AE technical 队列时重置）

## 5. Academic 预审阶段

### 5.1 当前设计定位

Academic 预审是**外审前的一道可选学术把关分支**，不是 first decision，也不是 final decision。

AE 选择 `Academic` 后，稿件进入：

- `pre_check / academic`

并由具体绑定的 `academic_editor` 处理。

### 5.2 Academic Editor 当前可见能力

当前 Academic Editor Workspace 已支持：

1. `Open Details`
2. `Submit Academic Decision`

也就是说，学术编辑现在至少可以先看稿件详情，再决定下一步，不再是只对着列表做选择。

### 5.3 Academic 当前出口

学术编辑当前有两个正式出口：

#### A. Route to External Review

含义：

- 学术编辑认为该稿件应进入正式外审

结果：

- `status -> under_review`

#### B. Send to Decision Workspace

含义：

- 学术编辑建议该稿件不需要先外审，而应由编辑部考虑直接进入后续决策阶段

结果：

- 当前只记录 `recommendation = decision_phase`
- 稿件继续停留在 `pre_check / academic`
- 后续由编辑部在详情页执行真实流转（如 `status -> decision`）

### 5.4 当前实现的重要说明

当前系统里：

- `academic pre-check` recommendation-only
- 与
- `under_review -> decision`

只有在编辑部执行实际流转后，才会进入同一套 `Decision Workspace`。

因此，Academic 预审阶段现在是“学术建议”与“编辑部执行”分层：

- 学术编辑提交 recommendation
- 编辑部决定是否推进到 `decision`

一旦被推进到 `decision / decision_done`：

- 学术编辑 / 主编看到的是 recommendation-only 的 5 个标准学术结论：
  - `accept`
  - `accept_after_minor_revision`
  - `major_revision`
  - `reject_resubmit`
  - `reject_decline`
- 他们提交后不会直接改变稿件状态，也不会直接通知作者
- recommendation 会写入审计，供编辑部后续执行时参考
- 内部编辑进入同一个 `Decision Workspace` 时，仍保留 execute 模式，负责真正的状态流转与作者通知
- 当内部编辑执行 first/final decision 时，作者通知当前以 **email-first** 为主，站内通知仅作补充
- 若内部执行结果仍是粗粒度 `reject / minor_revision`，系统会优先尝试匹配最近一条 workflow bucket 一致的学术 recommendation，用其更细的模板键发送作者邮件，例如：
  - `reject -> reject_resubmit`
  - `minor_revision -> accept_after_minor_revision`
- 当前已补最小 route 级 smoke，锁定以下两条真实链路：
  - `pre_check/academic` 中 academic recommendation 提交后，由编辑部执行推进到 `under_review`，会分别写入 recommendation 与 execution 审计
  - `pre_check/academic` 中 academic recommendation 提交后，由编辑部执行推进到 `decision`，会分别写入 recommendation 与 execution 审计
  - `review-stage-exit` 进入 `first decision` 时，会向指定收件人发出 first decision request email，且邮件里携带新的 academic recommendation label
  - `final decision` 中内部执行粗粒度 `reject` 时，如最近 recommendation 为 `reject_resubmit`，作者邮件会优先使用 `decision_reject_resubmit`
- 当前已补最小前端 mocked Playwright smoke，锁定：
  - `Decision Workspace` execute mode 仍支持 draft + final submit
  - academic recommendation-only mode 会隐藏 draft 保存入口，并以 `Submit First Recommendation / Submit Final Recommendation` 作为唯一提交动作

## 6. Reviewer 外审阶段

### 6.1 Reviewer assignment 生命周期

当前系统使用以下状态：

1. `selected`
2. `invited`
3. `opened`
4. `accepted`
5. `submitted`
6. `declined`
7. `cancelled`

其含义为：

- `selected`：仅加入拟邀请名单，尚未真正发邮件
- `invited`：邀请邮件已成功发送
- `opened`：reviewer 已打开邀请页，但未表态
- `accepted`：reviewer 已接受邀请，可进入 workspace
- `submitted`：reviewer 已提交审稿报告
- `declined`：reviewer 已拒绝
- `cancelled`：编辑部主动终止该 reviewer assignment

### 6.2 Reviewer 当前入口

Reviewer 当前主入口为邮件中的 magic link：

- 可免登录进入邀请页
- 明确接受 / 拒绝
- 接受后进入 reviewer workspace

### 6.3 Reviewer 提交内容

当前 reviewer 提交的是：

- 给作者的评论
- 给编辑的 confidential note
- 可选附件

当前已去掉默认 `score 5` 这类无意义评分项。

### 6.4 多轮 reviewer 选择

当前系统在作者修回后：

- 不会自动把上一轮 reviewer 复制到当前轮
- reviewer assignment modal 会显式区分：
  - `Current Round Reviewers`
  - `Previous Round Reviewers`
- `Current Round Reviewers` 表示当前轮已经选入 reviewer list，可直接移除
- `Previous Round Reviewers` 只是上一轮 reviewer 的复用建议，不会自动算作当前轮已选
- 如果编辑部要继续沿用上一轮 reviewer，必须手动点击 `Add to Selection`

### 6.5 Reviewer 邮件发送前编辑

当前 reviewer email preview 弹窗已改成发送前 compose：

- `Subject` 可由 AE / ME 直接编辑
- `Email Body` 可由 AE / ME 直接在富文本编辑器中修改
- `Plain Text` 不再单独人工维护，而是根据当前 HTML 自动生成，只读展示
- 本次修改只影响当前这一封 reviewer 邮件
- 不会回写底层 `email_templates`
- 如果收件人改成非 reviewer 邮箱，仍只做 preview/test send，不推进 assignment 状态

## 7. AE 离开 Under Review 的规则

### 7.1 当前系统已放开的口径

为避免流程被系统卡死，当前代码已允许：

- `0` 份 review 也可以离开 `under_review`

是否继续等待 reviewer，由 AE 自行判断。

### 7.2 Review Stage Exit 的目标动作

当前 AE 在稿件详情页通过 `Exit Review Stage` 可选择：

1. `Direct Major Revision`
2. `Direct Minor Revision`
3. `Send to First Decision`
4. `Send to Final Decision`

### 7.3 Direct Major / Minor

含义：

- AE 不经过 decision workspace，直接把稿件推进到作者修回阶段

结果：

- `status -> major_revision`
  或
- `status -> minor_revision`

### 7.4 Send to First Decision

含义：

- AE 不直接做最终判断
- 而是把稿件提交给学术编辑 / 主编进入后续决策处理

当前 AE 必须同时提交：

- `requested_outcome`
- `recipient_emails`
- `note`

其中 `requested_outcome` 当前允许：

- `accept`
- `accept_after_minor_revision`
- `major_revision`
- `reject_resubmit`
- `reject_decline`

这表示：

- AE 给出推荐意见
- 但后续由学术编辑 / 主编在 Decision Workspace 中继续处理

### 7.5 Send to Final Decision

含义：

- 稿件直接进入最终决策阶段

结果：

- `status -> decision_done`

## 8. Reviewer 在退出外审时的处理规则

当 AE 退出 `under_review` 时，当前系统规则为：

### 8.1 自动取消

这些 reviewer 会被系统自动 `cancel`：

- `selected`
- `invited`
- `opened`

### 8.2 必须显式处理

这些 reviewer 不能被系统自动跳过：

- `accepted but not submitted`

AE 必须对其逐个明确处理，例如：

- 继续等待
- 取消该 reviewer

## 9. Decision 阶段当前规则

### 9.1 decision

当前 `decision` 阶段允许：

- `minor_revision`
- `major_revision`
- `reject`
- `add_reviewer`

### 9.2 decision_done

当前 `decision_done` 阶段允许：

- `accept`
- `minor_revision`
- `major_revision`
- `reject`

### 9.3 当前明确限制

系统当前明确限制：

- `first decision` 不允许 `accept`
- `accept` 只出现在 `final decision` 阶段

### 9.4 作者通知

当前 `Decision Workspace` 在编辑部执行 first/final decision 后：

- 会给作者发送 decision email
- 同时保留一条站内 decision notification 作为补充
- email 使用明确的 `template_key`

当前已落地的 decision email template key 包括：

- `decision_accept`
- `decision_accept_after_minor_revision`
- `decision_major_revision`
- `decision_minor_revision`
- `decision_reject`
- `decision_reject_resubmit`
- `decision_reject_decline`

## 10. Production / Publish 阶段（2026-03-13 更新）

### 10.1 当前入口口径

录用后的 production 流程，当前已经切换为：

- 由 `production workspace` 作为唯一主操作入口
- 由 `production_cycles.stage + status` 承载详细生产阶段

当前不再建议通过稿件详情页直接推进 production。

也就是说：

- 稿件详情页主要承担摘要与跳转入口
- 详细排版 / 校对 / 发布动作集中在 production workspace

### 10.2 当前发布规则

当前系统里，最终发布只允许：

- `approved_for_publish -> published`

不会再沿用旧的：

- `layout -> english_editing -> proofreading -> published`

这种直接靠 `manuscript.status` 推进的 legacy 旁路。

### 10.3 当前 publish gate

发布前，当前系统会同时检查：

- Payment Gate
- Production Publish Gate
- 如启用 `PRODUCTION_GATE_ENABLED=1`，还会检查 `final_pdf_path`

若 production cycle 尚未满足可发布条件，系统不会直接发布。

### 10.4 作者校对反馈

当前作者在 production proofreading 阶段提交反馈时，已支持：

- 仅上传带批注 PDF
- 不强制同时提交结构化 `correction_items`

这意味着作者可以直接提交批注稿，由编辑部后续在 production workspace 继续处理。

### 10.5 当前 schema / migration 行为

若线上缺少 production SOP 所需 schema，当前接口不会再静默回退到旧逻辑。

当前统一行为是：

- 返回 `503`
- detail 以 `Production SOP schema not migrated: ...` 明确提示缺失的表或列

这条口径已覆盖 production workspace、publish gate、author feedback 等关键入口。

## 11. 当前已实现但仍建议验收方重点确认的点

以下并非系统错误，但建议验收方重点确认是否符合最终业务口径：

### 11.1 Academic 预审与 Decision Workspace 共用同一决策空间

当前实现中：

- academic pre-check 先记录 recommendation，再由编辑部决定是否送入 decision
- 外审结束后送入 decision

都会进入同一套 `Decision Workspace`

这比旧实现更符合业务边界，但是否还需要单独的“待编辑部执行 academic recommendation”看板，仍建议验收时确认。

### 11.2 AE 可直接给 major/minor

当前系统已支持：

- AE 在 `under_review` 阶段直接给 `major_revision`
- AE 在 `under_review` 阶段直接给 `minor_revision`

是否将这条作为最终长期规则，建议由验收方明确确认。

### 11.3 AE 不直接 reject，而是通过 first decision recommendation 表达

当前系统方向已在向：

- AE 不直接 reject
- AE 可 `send_first_decision + reject_resubmit / reject_decline recommendation`

收口。

这条建议继续作为正式业务规则进行验收确认。

## 12. 总结

当前系统已实现的真实流程可以概括为：

1. 作者投稿 -> 技术预审
2. ME 分配 AE
3. AE 技术检查后：
   - 直接外审
   - 送学术预审
   - 技术退回
4. 学术预审后：
   - 外审
   - 或直接进入 decision workspace
5. reviewer 可完成邀请、接受、提交、取消
6. AE 在外审阶段不必等待全部 reviewer 完成，即可推进：
   - direct major/minor
   - first decision
   - final decision

当前系统的主干流程已经打通，主要剩余工作集中在：

- 部分语义进一步收细
- 决策边界继续压实
- 邮件与审计体验继续增强
