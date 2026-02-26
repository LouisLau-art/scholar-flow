# Regression Checklist - UI Guideline Remediation

## US1: 可访问表单与弹窗闭环

- [x] 登录页表单 `label + htmlFor/id` 完整。
- [x] 注册页表单 `label + htmlFor/id` 完整。
- [x] Header 搜索弹窗输入具备显式 label。
- [x] 审稿提交表单输入具备显式 label。
- [x] Reviewer Dashboard / Reviewer Assign Dialog 不再使用隐藏默认关闭按钮 hack。
- [x] 弹窗可通过 `Esc` 与关闭按钮退出，并保持可访问路径。

## US2: 语义化交互与键盘可达

- [x] Header 无 `href="#"` 占位导航。
- [x] Mega Menu 分类项改为真实 `Link`。
- [x] Footer 资源区改为真实 `Link`。
- [x] Hero Trending 改为真实 `Link`。
- [x] Home Subject 卡片改为可语义导航 `Link`。

## US3: 文案与时间一致性

- [x] 目标加载文案统一为 `…`。
- [x] 编辑链路关键组件时间展示统一使用 `date-display`。
- [x] 反馈表时间展示统一使用 `date-display`。

## Validation Logs

- `bun run lint`: pass
- `bun run audit:ui-guidelines`: pass
- `bun run test:run src/tests/auth-pages.accessibility.test.tsx`: pass
- `bun run test:run tests/unit/rbac-visibility.test.ts`: pass
- `bun run test:run (performance suite)`: pass
- `./scripts/test-fast.sh`: pass

## Evidence (2026-02-26)

- Header/Mega Menu/Footer/Hero 交互项：已无 `href="#"` 与 `cursor-pointer` 伪交互。
- ReviewerDashboard / ReviewerAssignModal：已移除 `[&>button]:hidden` 关闭按钮 hack。
- 关键路径表单：登录、注册、站点搜索、审稿提交、管理员筛选均具备 label 绑定。
