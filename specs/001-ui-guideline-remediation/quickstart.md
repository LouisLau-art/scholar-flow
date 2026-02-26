# Quickstart - UI Guideline Remediation

## 1. 前置条件

1. 位于分支：`001-ui-guideline-remediation`
2. 前端依赖已安装：`cd frontend && bun install`
3. 本地可启动前端：`bun run dev`

## 2. 实施顺序（建议）

1. P1 可访问性修复  
2. P2 语义交互修复  
3. P3 一致性修复（文案/时间）

## 3. 本地验证命令

```bash
# 代码质量
cd /root/scholar-flow/frontend
bun run lint

# UI 规范静态审计
bun run audit:ui-guidelines

# 单测（按需）
bun run test:run

# Analyze 补偿测试（auth a11y）
bun run test:run src/tests/auth-pages.accessibility.test.tsx

# 性能证据测试（既有性能回归用例）
bun run test:run \
  src/tests/pages/editor-workspace.page.performance.test.tsx \
  src/components/editor/__tests__/manuscripts-process-panel.performance.test.tsx \
  src/components/editor/__tests__/audit-log-timeline.performance.test.tsx \
  "src/app/(admin)/editor/manuscript/[id]/__tests__/page.performance.test.tsx"
```

```bash
# 项目级快速回归（仓库根目录）
cd /root/scholar-flow
./scripts/test-fast.sh
```

## 4. 人工验收清单（关键路径）

### A. 表单与标签（P1）

1. `/login`：邮箱/密码均有可访问标签，键盘可完成提交。
2. `/signup`：邮箱/密码均有可访问标签，键盘可完成提交。
3. Header 搜索弹窗：输入框可被读屏识别为带标签输入。
4. 管理员用户筛选：搜索输入具备标签。

### B. 弹窗与键盘闭环（P1）

1. 任一业务弹窗可通过键盘关闭。
2. 关闭后焦点回到触发按钮。
3. 无“只能鼠标关闭”的路径。
4. 不依赖 `[&>button]:hidden` 这类样式 hack 隐藏关闭按钮。

### C. 语义交互（P2）

1. `cursor-pointer` 的可点击项必须是 `Link`/`button`。
2. 不存在 `href="#"` 占位导航。
3. 导航/页脚/Mega Menu 可通过键盘遍历并触发。

### D. 一致性（P3）

1. 加载文案统一使用 `…`。
2. 用户可见时间字段走统一 locale-aware 展示策略。
3. 通过 `bun run audit:ui-guidelines` 无违规项。

## 5. 完成定义（DoD）

1. `problem.md` 中本轮纳入范围的问题状态更新为已关闭。
2. 不新增后端接口，不改变权限语义。
3. `lint` 与定向回归通过，关键路径人工验收通过。
4. Analyze 补偿文档齐全：`performance-goals.md` + `permission-regression.md`。
