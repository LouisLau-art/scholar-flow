# Next 16 Stabilization Notes

日期：2026-03-06
阶段：升级前基线记录（pre-upgrade baseline）

## 当前代码锚点

- 基线 commit：`03c245b`
- 计划文档：`docs/plans/2026-03-06-next16-stabilization-plan.md`
- 预期回退 tag：`pre-next16-full-align`

## 当前前端依赖状态

- `next`: `16.1.6`
- `react`: `^18`
- `react-dom`: `^18`
- `eslint-config-next`: `14.2.0`
- `@types/react`: `^18`
- `@types/react-dom`: `^18`

结论：当前仓库处于明显的“半升级”状态：`Next 16 + React 18 + eslint-config-next 14`。

## 当前已知阻断 / 风险

1. `frontend/src/app/review/[token]/page.tsx` 在 `Next 16` 下已出现实际构建阻断：`ParamValue` 不能直接当 `string` 使用。
2. `frontend/src/middleware.ts` 仍沿用旧的 `middleware` 约定，需按 `Next 16` 迁到 `proxy`。
3. `frontend/next.config.mjs` 仍含过期/无效配置，需在正式升级时一起清理。
4. `frontend/src/app/(public)/review/error/page.tsx` 等页面对 `searchParams` 的读取仍未完全对齐 async request APIs。
5. `README.md` 与 `AGENTS.md` 仍保留 `Next.js 14` 的口径，和真实代码栈不一致。

## 当前文档/仓库口径不一致点

- `README.md` badge 仍显示 `Next.js 14`
- `README.md` Tech Stack 仍写 `Next.js 14`
- 仓库真实运行依赖已是 `Next.js 16.1.6`

## 当前 CI / 发布基线说明

- 本地基线以 `03c245b` 为准。
- 本次稳定化执行前，不引入 reviewer 业务功能变更。
- 升级执行将拆成独立提交：
  - 回退锚点 / 基线
  - toolchain guard
  - 依赖对齐
  - route/proxy/tooling 修复
  - 文档同步

## 官方文档约束（Context7 对齐）

- `Next.js 16.1.6` 要求继续完成 async request APIs 迁移：`params`、`searchParams`、`cookies()`、`headers()`。
- `middleware` 已迁移到 `proxy` 命名约定，官方提供 codemod。
- `eslint-config-next` 应与 `next` 主版本对齐。
- 官方提供 `next-async-request-api` 与 `middleware-to-proxy` codemod，应优先使用后再做人工清理。

## 执行边界

- 本阶段只处理前端框架稳定化。
- 不在这批提交中夹带 reviewer 产品改造。
- 若预览部署失败，直接按升级提交范围 `git revert`，回到 `pre-next16-full-align` 基线附近。
