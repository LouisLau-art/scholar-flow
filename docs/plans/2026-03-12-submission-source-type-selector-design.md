# Submission Source Type Selector Design

**Date:** 2026-03-12

## Goal

把作者投稿页里 `Word manuscript` 与 `LaTeX source ZIP` 的交互，从“两个上传框同时存在 + 自动替换”改成真正清晰的二选一流程。

核心目标不是继续加校验，而是让作者在 UI 上一开始就理解：

- `PDF manuscript` 必传
- `Cover letter` 必传
- `Word manuscript` 与 `LaTeX source ZIP` 只能二选一

## Problem Statement

当前实现虽然在技术上已经支持 `Word XOR ZIP`，但交互模型仍然不够清晰：

1. 页面同时展示 `Word` 和 `ZIP` 两个上传框，容易让作者误以为两者都可以一起提交。
2. 现有“上传第二个文件时自动替换第一个”的行为是隐式的，作者看不出系统到底做了什么。
3. 即使后端保留 XOR 校验，作者仍然会在前端形成错误预期。

这不是单纯的校验问题，而是心智模型不对。

## Confirmed Rules

1. `PDF manuscript` 必传。
2. `Cover letter` 必传。
3. `Word manuscript` 与 `LaTeX source ZIP` 只能二选一。
4. `LaTeX source` 当前只支持 `.zip`。
5. ZIP 只用于编辑部保存，不参与 AI / Gemini / 本地规则元数据解析。
6. 后端继续保留 XOR 校验，作为最终防线。

## Approaches Considered

### Approach A: 保留两个上传框，但互相禁用

做法：

- 页面继续同时展示 `Word` 和 `ZIP` 两个上传卡片。
- 一旦选了其一，另一个卡片禁用。
- 如果要切换，必须先点 `Remove` 清空当前已选文件。

优点：

- 改动范围较小。
- 对现有代码侵入低。

缺点：

- 页面仍然同时存在两个上传框，用户第一眼仍会误解为“两者都能传”。
- 只是“技术上拦住”，不是“交互上讲清楚”。

### Approach B: 先选 Manuscript Source Type，再显示单一上传区

做法：

- 在文件区增加一个 `Manuscript source` 选择器：
  - `Word manuscript (.doc/.docx)`
  - `LaTeX source ZIP (.zip)`
- 只显示当前选中的那一种上传卡片。
- 另一种上传卡片不出现。

优点：

- 用户心智最清楚。
- 从页面结构上消除歧义，不依赖错误提示教育用户。
- 后续如果还要扩展新的稿件源类型，也更容易收口。

缺点：

- 要多做一层前端状态管理和切换确认。

### Approach C: 继续允许两个上传框并自动替换

不推荐。

原因：

- 它会制造“我明明两个都上传了，系统为什么自己改了”的不透明行为。
- 这类隐式 destructive action 的 UX 很差，也容易造成支持成本。

## Recommendation

采用 **Approach B**。

也就是：

- 先让作者明确选择 `Manuscript source type`
- 再只展示对应的单一上传入口

这是当前最符合真实业务规则、同时最不容易误导作者的方案。

## UX Design

### File Section Layout

投稿页文件相关区域按这个顺序展示：

1. `Cover Letter (Required)`
2. `Manuscript Source (Choose One)`
3. `Source-specific upload card`
4. `PDF Manuscript (Required)`

其中：

- `Cover letter` 与 `PDF` 继续独立上传
- `Word/ZIP` 不再并排展示两个上传框

### Manuscript Source Selector

新增一个明确的单选选择器：

- `Word manuscript (.doc/.docx)`
- `LaTeX source ZIP (.zip)`

交互规则：

- 初始状态未选择，上传卡片不显示
- 选中 `Word` 后，只显示 `Word manuscript` 上传卡片
- 选中 `ZIP` 后，只显示 `LaTeX source ZIP` 上传卡片

### Switching Source Type

如果作者已经为当前 source type 上传了文件，再切换到另一种类型时，必须弹确认。

确认文案建议：

- Title: `Switch manuscript source type?`
- Body:
  - `This will remove the current Word manuscript.`
  - 或 `This will remove the current LaTeX source ZIP.`
  - `PDF manuscript and cover letter will be kept.`

按钮建议：

- Secondary: `Cancel`
- Primary: `Switch and Remove Current File`

### Uploaded State

上传成功后，只在当前 source type 卡片中显示：

- 文件名
- 上传成功状态
- `Remove`
- `Switch source type`

不再显示另一路的上传框，也不做静默替换。

## Behavior Rules

### Frontend

1. 只有在已选择 source type 后，才允许上传对应文件。
2. 未选择 source type 时，Finalize 按钮保持不可用。
3. 如果当前 source type 已上传文件，切换类型必须先确认。
4. 确认切换后：
   - 清空当前 Word 或 ZIP 的本地状态
   - 重置对应 file input
   - 保留 PDF 与 Cover Letter

### Backend

后端保持现有强校验，不因为 UX 改善而放松：

- `file_path` 必须存在
- `cover_letter_path` 必须存在
- `manuscript_word_path XOR source_archive_path`

也就是说：

- 前端负责“讲清楚”
- 后端负责“兜住底”

## Testing Strategy

遵循 `AGENTS.md` 的最小验证原则，只覆盖这次 UX 变更直接相关的行为：

### Frontend

1. 未选择 source type 时，不显示 source upload card 或按钮不可提交。
2. 选择 `Word` 后，只显示 `Word` 上传卡片。
3. 选择 `ZIP` 后，只显示 `ZIP` 上传卡片。
4. 已上传 `Word` 时切换到 `ZIP` 会弹确认。
5. 已上传 `ZIP` 时切换到 `Word` 会弹确认。
6. 确认切换后，旧 source 被清空，新 source 可上传。

### Backend

后端只保留现有最小回归：

1. `pdf + cover + word` 成功
2. `pdf + cover + zip` 成功
3. `word + zip` 同时出现返回 422
4. 二者都缺失返回 422

## Success Criteria

作者在投稿页不会再出现以下误解：

- “Word 和 ZIP 看起来都能上传，所以我可以两个都传”
- “系统为什么偷偷把我另一个文件替换了”

作者应该清楚感知到：

- 我必须先选一种 source type
- 我一次只能走一条路线
- 如果要换路线，需要我自己确认

## Out of Scope

本轮不做：

- ZIP 解压
- ZIP 元数据解析
- revision 流程同步改造
- `.rar/.7z/.tar.gz`
- 编辑端文件仓库的大改版
