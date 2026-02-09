# OSS 架构对标矩阵（OJS + Janeway）

**更新时间**: 2026-02-09  
**范围**: 仅做能力对标，不复制第三方实现代码。

## 对标原则
- 抄“能力模型与流程颗粒度”，不抄语言实现和源码。
- 以 `reference1~reference5` 作为业务最终裁判。
- 所有对标项必须落到 ScholarFlow 的 `API + UI + 测试` 三位一体验收。

## 能力矩阵
| 能力域 | OJS / Janeway 参考 | ScholarFlow 现状 | 结论 | 下一步 |
|---|---|---|---|---|
| 投稿-外审-决策-生产主链路 | OJS Workflow Stages；Janeway workflow guides | 已打通（含 reviewer workspace / decision workspace / production workspace） | 已对齐 | 持续做稳定性回归 |
| 角色与作用域 | OJS 的 context role；Janeway 的 journal-manager / editor / section-editor / production 等 | 现有 `author/reviewer/editor/admin` 可运行，但粒度偏粗 | 部分缺口 | 做 `GAP-P1-05`（角色矩阵 + journal-scope RBAC） |
| 决策工作台 | OJS Decisions；Janeway draft decisions | 已有 Final Decision Workspace + 审计 | 基本对齐 | 补 `first decision` 显式语义 |
| 审稿邀请生命周期 | Janeway reviewer invite/access + due metadata | 已有 invite/accept/decline timeline 与 magic link | 部分缺口 | 做 `GAP-P1-04`（冷却期、due date 窗口、模板） |
| 引用导出 | Janeway/OJS 都支持结构化元数据对外分发 | 已新增 BibTeX/RIS 导出接口 | 已对齐 | 补端到端回归与用户反馈 |
| Subject Collections | Janeway repo/subject 体系 | 已由 `/api/v1/public/topics` 动态聚合 | MVP 对齐 | 后续引入真实 subject 字段替代关键词推断 |
| Scholar/SEO 元数据 | Scholar/Crossref 友好 metadata | 已输出 citation tags，并补 `citation_pdf_url` | 基本对齐 | 后续增加自动校验脚本 |
| DOI / Crossref | OJS/Janeway 均有成熟链路 | 当前仍为占位/部分能力 | 缺口 | `GAP-P2-01` |
| 查重 | 常见平台为可插拔外部服务 | 默认关闭 | 缺口 | `GAP-P2-02` |

## 立即执行序列
1. [x] 完成 `GAP-P1-04`：邀请策略（冷却期 + due date + 模板）。
2. [x] 完成 `GAP-P1-05`：角色矩阵与期刊作用域 RBAC（含 `/editor/rbac/context`、前端 capability 显隐、跨刊 403 集成测试、mocked E2E）。
3. [ ] 进入 `GAP-P1-03`：Analytics 管理视角增强（编辑效率排行 + 阶段耗时 + SLA 预警）。
