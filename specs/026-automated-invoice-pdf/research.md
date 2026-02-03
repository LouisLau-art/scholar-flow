# Research: Automated Invoice PDF (Feature 026)

**Date**: 2026-02-03  
**Branch**: `026-automated-invoice-pdf`  

## Decisions

### 1) PDF 引擎

**Decision**: 使用 WeasyPrint（HTML → PDF）。

**Rationale**:
- HTML/CSS 模板开发效率高，可快速做出“正式账单”的专业排版。
- 与现有 Jinja2 模板体系契合（邮件模板已在用）。

**Alternatives considered**:
- ReportLab：纯代码排版可控，但开发慢且难以达到“网页级”的样式迭代速度。
- 纯前端生成：在安全与一致性（字体/排版）上更难控制，且需要额外下载/渲染逻辑。

### 2) 容器/部署依赖（WeasyPrint 系统包）

**Decision**: 在后端 Docker 镜像中通过 APT 安装 WeasyPrint 所需系统依赖与字体包。

**Rationale**:
- WeasyPrint 依赖 Cairo/Pango 等系统库；不在镜像层安装会导致运行时报错。

**Minimum expected deps (Debian/Ubuntu)**:
- `libcairo2`
- `libpango-1.0-0`
- `libpangocairo-1.0-0`
- `libgdk-pixbuf2.0-0`
- `shared-mime-info`
- 字体：`fonts-dejavu-core`（或 `fonts-liberation`）

### 3) Storage 安全模式（避免回填短期 URL）

**Decision**: `invoices` 桶保持私有；数据库只保存 **稳定的 storage path**（不保存 signed URL）；下载时由后端生成短期 `signed_url` 返回给前端。

**Rationale**:
- signed URL 有过期时间，保存到 DB 会导致“过期链接”。
- 私有桶 + 后端签名能保持最少权限面与一致的访问控制。

**Alternatives considered**:
- public bucket + public URL：实现简单但不满足“作者专属 + 内部可见”的访问控制底线。
- 后端直接流式转发 PDF：可行但会增加后端带宽与实现复杂度；signed URL 更轻。

### 4) Invoice Number 生成策略

**Decision**: `INV-{YYYY}-{invoice_id_short}`（例如 `INV-2026-1A2B3C4D`）。

**Rationale**:
- 人类可读、可在 UI/邮件里展示。
- 不依赖全局序列或额外计数器，避免并发/迁移复杂度。

### 5) 幂等与再生成

**Decision**:
- 一个稿件只对应一个 invoice record（已存在 `manuscript_id UNIQUE` / `upsert on_conflict=manuscript_id`）。
- PDF 再生成会 **覆盖同一路径** 的 PDF 文件（或替换 path），但不改变 `invoices.status/confirmed_at`。

**Rationale**:
- 重复点击 Accept 或后台重试不会产生重复账单。
- 业务允许更改金额后再生成，但不能“抹掉已付款”事实。

