# Email Templates (React Email)

本目录用于邮件模板工程化维护（React 组件化），避免长期手写 HTML。

## 生成模板 JSON

在 `frontend/` 目录执行：

```bash
bun run email:build-templates
```

会生成：

`emails/generated/reviewer-assignment.templates.json`

该文件可用于：

- Admin 模板管理页面批量导入；
- 与 Supabase `email_templates` 表做种子同步。

## 变量约定

当前模板使用和后端一致的 Jinja 占位符：

- `{{ reviewer_name }}`
- `{{ manuscript_title }}`
- `{{ manuscript_id }}`
- `{{ journal_title }}`
- `{{ due_date or due_at or '-' }}`
- `{{ review_url }}`
- `{{ cancel_reason }}`
