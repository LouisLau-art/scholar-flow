# Phase 0 Research - UI Guideline Remediation

## Decision 1: 关键表单统一“显式可访问标签”
- **Decision**: 对关键路径输入控件统一采用显式 `label + htmlFor/id`；空间受限场景使用 `sr-only` label，不再依赖 placeholder 充当标签。
- **Rationale**: placeholder 不稳定且不具备完整可访问语义，读屏与键盘用户体验不可靠。
- **Alternatives considered**:
  - 仅添加 `aria-label`：可用但难统一维护，且可见性弱。
  - 保留 placeholder-only：不满足无障碍最佳实践。

## Decision 2: 弹窗统一复用 shadcn Dialog 关闭语义
- **Decision**: 业务弹窗统一复用 `Dialog`，保留默认关闭能力或使用 `DialogClose asChild`；禁止手写遮罩弹窗作为主实现。
- **Rationale**: 统一焦点管理、Esc 行为、可访问语义，减少重复维护。
- **Alternatives considered**:
  - 继续手写弹窗：每个弹窗都要重复处理焦点与键盘边界，回归成本高。

## Decision 3: 交互元素语义化（Link/Button）并清理伪交互
- **Decision**: 所有可点击入口使用 `Link` 或 `button`；清理 `cursor-pointer` 但无行为或无语义节点。
- **Rationale**: 键盘可达性、可测试性和用户预期一致性显著提升。
- **Alternatives considered**:
  - 保留伪交互 + JS 补丁：短期可行但语义不完整、维护复杂。

## Decision 4: 占位导航入口 `href="#"` 必须下线或替换
- **Decision**: 对尚未开放路径，改为真实链接或禁用态动作（带清晰文案），不允许回顶空跳。
- **Rationale**: 避免误导与“无反馈交互”。
- **Alternatives considered**:
  - 继续使用 `#`：对用户无实际价值，并造成导航噪音。

## Decision 5: 焦点可见性采用统一规范
- **Decision**: 不允许全局 `focus:outline-none + focus:ring-0` 直接清空焦点；统一保留 `focus-visible` ring。
- **Rationale**: 键盘用户需要明确焦点位置；符合 Web 可访问性基线。
- **Alternatives considered**:
  - 仅鼠标优化视觉：牺牲键盘可用性，不可接受。

## Decision 6: 文案省略号统一为 `…`
- **Decision**: 所有加载/处理中提示统一单字符省略号 `…`，禁止 `...` 混用。
- **Rationale**: 全站文案排版一致，避免视觉噪声。
- **Alternatives considered**:
  - 不统一：持续产生页面风格割裂。

## Decision 7: 日期时间统一走 locale-aware 工具
- **Decision**: 页面展示层优先复用 `frontend/src/lib/date-display.ts`，避免散落的固定模板格式。
- **Rationale**: 降低跨区域展示不一致风险，减少重复格式化逻辑。
- **Alternatives considered**:
  - 各页面自行 `date-fns format(...)`：一致性不可控，迁移成本持续上升。

## Decision 8: API 层保持“兼容不变”，只做 UI 回归契约
- **Decision**: 本特性不新增后端接口，仅建立关键交互所依赖的既有 API 契约快照（用于回归保护）。
- **Rationale**: 需求本质是 UI 规范修复；后端改动会扩大风险面。
- **Alternatives considered**:
  - 新增“专用校验接口”：收益低且会增加维护面。
