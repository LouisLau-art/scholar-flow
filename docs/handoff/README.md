# ScholarFlow 交接文档索引

更新时间：2026-03-17

本目录现在按三类文档组织，分别服务于管理侧、技术接手人、以及后续继续接手本项目的 AI agent。

## 1. 总交接总览

文件：

- `2026-03-17-platform-account-transition-handover.md`
- `2026-03-17-platform-account-transition-handover.pdf`

适用对象：

- 管理侧
- 技术接手人
- 需要快速判断“哪些平台已经接住、哪些还没彻底去个人化”的人

用途：

- 看五个平台的当前状态
- 看本次交接已完成到哪一步
- 看哪些风险仍然存在但暂时不是 blocker

## 2. 技术接手 Runbook

文件：

- `2026-03-17-technical-successor-cutover-runbook.md`
- `2026-03-17-technical-successor-cutover-runbook.pdf`

适用对象：

- 负责继续维护 ScholarFlow 的技术同事

用途：

- 直接照着执行最小运维动作
- 遇到故障时快速判断先查哪一层
- 在不依赖原负责人账号的前提下继续把系统跑起来

## 3. AI / Agent 上下文包

文件：

- `2026-03-17-ai-operator-context-pack.md`
- `2026-03-17-ai-operator-context-pack.pdf`

适用对象：

- 未来继续接手 ScholarFlow 的 AI agent
- 需要把上下文一次性喂给大模型的技术同事

用途：

- 提供结构化、低歧义、便于模型消费的上下文
- 提供事实快照、命令入口、停止条件、常见故障判断
- 减少“重新摸索项目与平台状态”的成本

## 4. 当前建议的使用顺序

如果目标是继续把系统跑起来：

1. 先看技术接手 Runbook
2. 再看 AI / Agent 上下文包
3. 最后看总交接总览

如果目标是做正式离职交接：

1. 总交接总览给管理侧与多角色一起看
2. 技术接手 Runbook 给技术同事执行
3. AI / Agent 上下文包留作后续持续维护资料
