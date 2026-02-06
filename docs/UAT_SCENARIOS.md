# UAT 验收测试场景 (UAT Scenarios)

本文档旨在指导相关人员（主编、投资人、财务等）对 ScholarFlow 平台进行用户验收测试 (UAT)。

**测试环境**: [预发布环境 (Staging)](https://staging.scholarflow.example.com)
**识别标志**: 请确认屏幕底部显示黄色的 "UAT Staging" 横幅。

---

## 🐞 如何反馈问题

如果您在测试过程中遇到问题或有任何建议：
1. 点击屏幕右下角的 **Bug 图标** (🐞)。
2. 选择严重程度 (低 Low, 中 Medium, 严重 Critical)。
3. 描述您遇到的问题以及您的预期结果。
4. 点击 **Submit (提交)**。系统会自动记录您的反馈及相关技术信息。

---

## 场景 A：处理学术不端 (Academic Misconduct Handling)

**角色**: 主编 (Editor)
**目标**: 识别一篇可疑的稿件并将其永久拒稿。

**前置条件**:
1. 联系开发团队运行 "重置数据 (Reset Data)" 脚本，初始化测试数据。
2. 使用账号 `editor@scholarflow.test` 登录 (密码: `password123`)。

**操作步骤**:
1. 进入 **Editor Dashboard (主编工作台)**。
2. 找到标题为 "Quantum Entanglement at Macroscopic Scales" (或类似的待处理稿件)。
3. 点击进入详情页。
4. 如果当前状态不是 `decision` / `decision_done`，先在 **Change Status** 中将稿件推进到决策阶段（例如 `Move to Decision Done`）。
5. 找到 **Decision (决策)** 面板。
6. 选择 **Reject (拒稿)**。
7. 在拒稿理由中选择 **Academic Misconduct (学术不端)**。
8. 确认提交决策。

**预期结果**:
- 稿件状态变更为 `Rejected`。
- 投稿人收到拒稿通知邮件。
- 系统会在后台标记该作者，供未来审稿参考。

---

## 场景 B：财务审核与放行 (Finance Approval)

**角色**: 管理员 / 财务 (Administrator / Finance)
**目标**: 确认版面费 (APC) 到账并发布文章。

**前置条件**:
1. 重置预发布环境数据库。
2. 使用 `editor@scholarflow.test` 登录 (在 UAT 环境中，该账号拥有管理员权限)。

**操作步骤**:
1. 进入 **Manuscripts (稿件)** 列表页。
2. 筛选状态为 `Accepted` (已录用)。
3. 找到等待付款的稿件。
4. 点击 **Manage Payment (管理付款)**。
5. 选择 **Mark as Paid (手动标记为已付)**。
6. 确认操作。

**预期结果**:
- 稿件状态变更为 `Published` (已发布) 或 `Production` (出版中)。
- 文章全文在前台可见。
