# Handoff: Opencode Antigravity Configuration

**Created:** 2026-03-12 21:33:00
**Project:** /root/scholar-flow
**Git Branch:** main
**Recent Commits:**
- a7e9110 fix(editor): invalidate managing workspace cache on mutations
- bc232f0 feat: complete production sop transition logic, queues, and artifact logging
- 8b8175a fix(editor): harden workspace auth gate and error state
- 8aa5de6 refactor(editor): reuse managing workspace from intake route
- 23d17fd feat(editor): add managing workspace quick actions

---

## Current State Summary

刚刚完成了 Opencode CLI 的 Antigravity OAuth 插件配置，让 Opencode 可以使用 Google Antigravity 提供的模型：

1. **已配置插件**: `opencode-google-antigravity-auth`
2. **已配置模型**:
   - Gemini 3.1 Pro (`gemini-3.1-pro-preview`)
   - Gemini 3 Flash (`gemini-3-flash`)
   - Claude Sonnet 4.6 (`gemini-claude-sonnet-4-6-thinking`)
   - Claude Opus 4.6 (`gemini-claera-opus-4-6-thinking`)
3. **配置文件位置**: `/root/.opencode/opencode.json`
4. **下一步**: 运行 `opencode auth login` 完成 Google OAuth 认证

---

## Important Context

### Opencode 配置文件位置
- **主配置**: `/root/.opencode/opencode.json`
- **插件依赖**: `/root/.opencode/package.json`

### Antigravity 模型配置规则

**Gemini 模型**使用 `thinkingLevel`:
- `minimal`, `low`, `medium`, `high`

**Claude 模型**使用 `thinkingBudget`:
- `none` (无思维模式)
- `low` (4000 tokens)
- `medium` (16000 tokens)
- `high` (32000 tokens)

### 多账号负载均衡
插件支持登录多个 Google 账号，自动轮询使用以避免速率限制：
- 第 1 次请求 → 账号 A
- 第 2 次请求 → 账号 B
- 第 3 次请求 → 账号 C
- 第 4 次请求 → 账号 A (循环)

---

## Critical Files

| 文件 | 说明 |
|------|------|
| `/root/.opencode/opencode.json` | Opencode 主配置文件，已更新 Antigravity 模型 |
| `/root/.opencode/package.json` | 插件依赖管理 |

---

## Immediate Next Steps

1. [ ] 运行 `opencode auth login` 完成 Google OAuth 认证
2. [ ] 选择 "OAuth with Google (Antigravity)" 提供商
3. [ ] 在浏览器中完成认证
4. [ ] 测试模型: `opencode run -m google/gemini-3-flash -p "hello"`
5. [ ] 如需更多速率限制，可添加多个 Google 账号

---

## Decisions Made

| 决策 | 理由 |
|--------|------|
| 使用 `gemini-3.1-pro-preview` 而非 `gemini-3-pro-preview` | 用户明确指定使用 3.1 版本 |
| 使用 `gemini-claude-sonnet-4-6-thinking` 和 `gemini-claude-opus-4-6-thinking` | 用户明确指定使用 Claude 4.6 版本 |
| 保留原有的 volcengine 配置 | 避免破坏现有豆包模型配置 |

---

## Pending Work

- [ ] 完成 OAuth 认证
- [ ] 验证所有模型可用性
- [ ] 根据需要添加多账号负载均衡

---

## Key Patterns Discovered

- Opencode 配置文件使用 `$schema` 字段进行验证
- Google provider 需要指定 `npm: "@ai-sdk/google"`
- 模型 ID 必须与 Antigravity 后端支持的 ID 完全匹配

---

## Potential Gotchas

- 模型 ID 必须精确匹配，否则会返回 404
- Claude 模型使用 `thinkingBudget`，Gemini 模型使用 `thinkingLevel`，不要混淆
- 首次使用需要浏览器认证，headless 环境会降级为复制粘贴方式

---

## Modified Files Since Handoff

当前会话修改的文件：
- `/root/.opencode/opencode.json` - 添加 Antigravity 插件和模型配置
