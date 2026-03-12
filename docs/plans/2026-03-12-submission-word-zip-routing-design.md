# Submission Word/ZIP Routing Design

**Date:** 2026-03-12

## Goal

把作者投稿页的“主稿补充文件”规则改成符合真实期刊场景：

- `PDF manuscript` 必传
- `Cover letter` 必传
- `Word manuscript` 与 `LaTeX source ZIP` 互斥二选一
- `ZIP` 只存储，不参与 AI / 大模型元数据解析

## Confirmed Rules

1. 作者必须上传 PDF。
2. 作者必须上传 cover letter。
3. 作者必须在 `Word manuscript` 与 `LaTeX source ZIP` 中二选一。
4. 作者不能同时上传 Word 和 ZIP。
5. LaTeX source 当前只支持 `.zip`。
6. ZIP 不做解压、不做大模型解析、不做标题/摘要/作者抽取。
7. 如果作者走 ZIP 路线，元数据仍只依赖 PDF 解析或手填。

## Scope

本轮只改：

- 作者投稿前端
- 作者投稿后端校验
- `manuscript_files` 持久化
- 编辑详情页文件仓库展示
- 最小测试与文档

本轮不改：

- revision 提交流程
- ZIP 解压/预览/解析
- `.rar/.7z/.tar.gz`
- reviewer / editor 其他上传入口

## UX Design

### 上传区块

投稿页文件区调整为四块：

1. `Cover Letter (Required)`
2. `Word Manuscript (Optional)`
3. `LaTeX Source ZIP (Optional)`
4. `PDF Manuscript (Required)`

其中 2 和 3 是互斥组：

- 若已上传 Word，则 ZIP 上传入口禁用或再次选择时清空 Word。
- 若已上传 ZIP，则 Word 上传入口禁用或再次选择时清空 ZIP。

### 文案

- Word 卡片：
  - `Word Manuscript (.doc/.docx) (Optional)`
  - `Use this if you submit a Word-based manuscript.`
- ZIP 卡片：
  - `LaTeX Source ZIP (.zip) (Optional)`
  - `Use this if you submit a LaTeX manuscript. ZIP is stored for editorial use only and is not used for metadata parsing.`
- 提交提示：
  - `Upload PDF + cover letter + either Word manuscript or LaTeX ZIP.`

## Backend Design

### Request Model

`ManuscriptCreate` 改成支持：

- `manuscript_word_*` 可空
- 新增：
  - `source_archive_path`
  - `source_archive_filename`
  - `source_archive_content_type`

并通过 `model_validator(mode="after")` 做交叉字段校验：

- `file_path` 必须存在
- `cover_letter_path` 必须存在
- `manuscript_word_path` 与 `source_archive_path` 必须恰好存在一个

### Upload Endpoint

`POST /api/v1/manuscripts/upload` 保持“只用于解析的上传”定位：

- 支持：`.pdf/.doc/.docx`
- 不支持：`.zip`

ZIP 前端直接上传到 Storage，不调用该解析接口。

### Persistence

作者最终提交时：

- Word 路线：继续写 `file_type=manuscript`
- ZIP 路线：写 `file_type=source_archive`
- Cover letter：继续写 `file_type=cover_letter`

## Editor Detail Display

编辑详情页 `FileHubCard` 中：

- `source_archive` 归入 `Manuscript Versions`
- badge 显示 `ZIP`

这样无需新增第四个文件分组，先保持最小 UI 改动。

## Testing Strategy

遵循 `AGENTS.md` 的“最小验证”：

### 高风险点先补失败测试

- 后端：
  - `pdf + cover + word` 成功
  - `pdf + cover + zip` 成功
  - `pdf + cover + word + zip` 拒绝
  - `pdf + cover` 且两者都没传 拒绝
- 前端：
  - submit button 在 `pdf + cover + (word xor zip)` 前保持禁用
  - 选 Word 后 ZIP 入口禁用/互斥
  - 选 ZIP 后 Word 入口禁用/互斥
  - ZIP 上传不会调用 `/api/v1/manuscripts/upload`

### 最小回归

- 相关 Vitest
- 相关后端 pytest
- `bunx tsc --noEmit`

## Checklist

- [x] 设计确认
- [x] 实现计划落盘
- [x] 后端 schema / 校验改造
- [x] 前端互斥上传 UI 改造
- [x] 编辑详情页显示 `source_archive`
- [x] 最小测试通过
- [x] 文档同步
