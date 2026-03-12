# Reviewer Email Compose Design

**Date:** 2026-03-12

**Status:** approved for implementation

## Problem

当前 reviewer 邮件发送前弹窗存在三个核心问题：

1. 左侧 `HTML Preview` 与右侧 `Plain Text` 可能不一致。
2. `Subject / HTML / Plain Text` 都是只读，AE / ME 不能在发送前做最后一轮人工润色。
3. 当前弹窗是 `preview-only` 设计，不符合实际编辑部“看完直接改、改完直接发”的工作习惯。

## Confirmed Business Rules

- reviewer 邮件发送前，AE / ME 可以做本次发送专用的最终编辑。
- 这些编辑 **只影响本次发送**，**不能回写底层模板**。
- 底层模板仍由更高权限角色统一维护。
- 这次功能只覆盖 reviewer invitation / reminder 这条邮件链。

## Recommended Approach

采用 `Subject + HTML WYSIWYG editable, Plain Text derived read-only`。

### Source of Truth

- 本次发送的 `subject` 由弹窗内可编辑输入框维护。
- 本次发送的 `html body` 由弹窗内富文本编辑器维护。
- `plain text` 不再由用户单独维护，而是始终从当前 `html body` 自动派生。

这意味着 reviewer email compose 的最终发送源只有两份：

- `subject_override`
- `body_html_override`

后端发送时基于最终 HTML 重新派生 plain text，确保预览与真实发送一致。

## UX Model

### Dialog Layout

保留现有弹窗，但调整为 `compose + preview` 模式：

- 左侧：
  - `Subject` 可编辑
  - `Email Body` 富文本编辑器，可直接所见即所得修改正文
- 右侧：
  - `Recipient` 可编辑
  - 模板元信息卡片继续保留
  - `Plain Text` 只读，实时根据当前 HTML 自动生成

### Formatting Scope

首版只支持邮件安全且编辑部最常用的基础格式：

- bold
- italic
- underline
- bullet list
- ordered list
- link
- paragraph / line break

首版不支持：

- 图片上传
- 任意颜色
- 任意字号
- 表格
- 自定义 CSS
- 直接编辑 raw HTML

## Technical Design

### Frontend

复用现有 Tiptap 基础能力，新增 reviewer email 专用编辑器组件，而不是直接把现有 CMS editor 整体搬过来。

原因：

- reviewer email compose 只需要极小格式子集；
- 不需要图片上传；
- 需要与 plain text 派生、recipient override 警告、发送按钮状态强耦合；
- 单独组件更容易把行为锁死在 reviewer email 这一条链上。

前端状态建议拆成：

- `editableSubject`
- `editableHtml`
- `derivedPlainText`
- `recipientEmail`

其中：

- `editableSubject / editableHtml` 在打开 preview 时由后端初始渲染结果初始化；
- `derivedPlainText` 在前端根据 `editableHtml` 实时派生；
- `recipientEmail` 保留现有 override 语义。

### Backend

扩展 reviewer email preview / send payload：

- `subject_override?: string`
- `body_html_override?: string`

后端规则：

- preview 接口如果收到 override，则基于 override 返回最新 preview；
- send 接口如果收到 override，则按 override 发送；
- reviewer email send path 的 plain text 一律以最终 HTML 为源重新派生，不再信任独立 text template 作为发送正文来源。

这条规则只应用于 reviewer email compose/send，不影响 admin 模板管理页面继续保存 `body_text_template`。

## Consistency Rule

为彻底消除“左侧 HTML / 右侧 Plain Text / 实际发送内容”不一致：

1. 前端右侧 plain text 由当前 HTML 实时派生。
2. 后端真实发送前再次从最终 HTML 派生 plain text。
3. reviewer preview UI 不再把后端返回的独立 `text` 视为主要编辑源。

## Security / Safety

- 弹窗内编辑结果只在当前发送动作生效，不写回 `email_templates`。
- 仍保留当前 `recipient override = preview/test send` 语义。
- 富文本输出只允许 Tiptap 当前支持的基础标签子集，避免直接放开 raw HTML 输入。

## Known Tradeoff

如果底层 reviewer 模板未来包含复杂 HTML（如表格、复杂布局、内联样式块），首版 compose editor 可能会把它规范化为基础富文本结构。

这是可接受的当前 tradeoff，因为 reviewer invitation / reminder 模板当前是简洁文本邮件，编辑部真正需要的是最后一公里润色，而不是复杂邮件排版。

如果将来要支持复杂模板，应该走独立的“模板设计器”能力，而不是继续堆到这个发送前弹窗里。

## Files Likely Affected

- `frontend/src/components/editor/ReviewerEmailPreviewDialog.tsx`
- `frontend/src/components/editor/*`（new reviewer email compose editor helper）
- `frontend/src/app/(admin)/editor/manuscript/[id]/page.tsx`
- `frontend/src/app/(admin)/editor/manuscript/[id]/types.ts`
- `frontend/src/services/editor-api/manuscripts.ts`
- `backend/app/api/v1/reviews.py`
- `backend/app/core/mail.py`
- reviewer email preview/send related tests

## Minimal Success Criteria

- 打开 reviewer email preview 后，AE / ME 可以直接编辑 `Subject` 和正文。
- 右侧 `Plain Text` 会随正文变化自动更新。
- 发送时实际邮件使用用户本次编辑后的内容。
- 本次编辑不会修改底层模板。
- recipient 改成非 reviewer 邮箱时，仍只做 preview/test send，不推进 assignment 状态。
