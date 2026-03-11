# 当前系统已实现业务流程说明（给验收方）

更新时间：2026-03-11

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

作者首次投稿时，当前系统要求上传：

1. Cover Letter
2. Manuscript Word
3. Manuscript PDF

当前页面顺序也是：

1. Cover Letter
2. Word
3. PDF

### 2.2 元数据自动解析

当前系统已切换为：

- **DOCX-first**
- **PDF-fallback**

即：

- Word 稿成功解析出标题/摘要/作者信息后，Word 成为主元数据来源
- PDF 仍为必传文件，但不再与 Word 竞争元数据主来源

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

当前实现会将稿件推进到修回相关状态链，而不是继续停留在 technical pre-check。

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

- 学术编辑认为该稿件不需要先外审，而应直接进入后续决策阶段

结果：

- `status -> decision`

### 5.4 当前实现的重要说明

当前系统里：

- `academic pre-check -> decision`
- 与
- `under_review -> decision`

最终都会进入同一套 `Decision Workspace`。

因此，Academic 预审选择 `Send to Decision Workspace` 后，看到的仍然是：

- `minor revision`
- `major revision`
- `reject`
- `add reviewer`

这不是异常，而是当前实现的明确设计。

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

- `major_revision`
- `minor_revision`
- `reject`
- `add_reviewer`

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

## 10. 当前已实现但仍建议验收方重点确认的点

以下并非系统错误，但建议验收方重点确认是否符合最终业务口径：

### 10.1 Academic 预审与 Decision Workspace 共用同一决策空间

当前实现中：

- academic pre-check 送入 decision
- 外审结束后送入 decision

都会进入同一套 `Decision Workspace`

这在运行上是成立的，但在产品语义上仍偏粗。

### 10.2 AE 可直接给 major/minor

当前系统已支持：

- AE 在 `under_review` 阶段直接给 `major_revision`
- AE 在 `under_review` 阶段直接给 `minor_revision`

是否将这条作为最终长期规则，建议由验收方明确确认。

### 10.3 AE 不直接 reject，而是通过 first decision recommendation 表达

当前系统方向已在向：

- AE 不直接 reject
- AE 可 `send_first_decision + reject recommendation`

收口。

这条建议继续作为正式业务规则进行验收确认。

## 11. 总结

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
