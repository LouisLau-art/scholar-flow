# Quickstart: Core Logic Hardening

## Prerequisites

- Python 环境可用（Backend 可启动/可跑集成测试）
- Supabase：默认使用**云端 Supabase**（推荐用 Supabase CLI 同步 migration）
- 说明：`/api/v1/editor/*` 与 `/api/v1/reviews/feedback/*` 需要登录态（Bearer Token）；`/api/v1/reviews/token/*` 为免登录 Reviewer Token 流程

## Database Setup

1. Run the migration to add dual comment fields:
   ```bash
   # 在 repo root
   supabase db push --dry-run
   supabase db push
   ```

## Testing the Financial Gate

1. **Submit** a manuscript (Author).
2. **Review** it (Reviewer) - try adding confidential comments（通过 Reviewer Token 入口提交，见下方 curl 示例）。
3. **Accept** it (Editor) - **Set APC > 0** in the dialog（或调用 `/api/v1/editor/decision`）。
4. **Try to Publish** (Editor) - **Expect Failure (403)**.
   ```bash
   # 需要 editor/admin 的 Bearer Token
   curl -X POST "http://localhost:8000/api/v1/editor/publish" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"manuscript_id":"<uuid>"}'
   ```
5. **Simulate Payment**:
   - Manually update `invoices` table:
     `UPDATE invoices SET status = 'paid', confirmed_at = now() WHERE manuscript_id = '...'`
6. **Try to Publish** (Editor) - **Expect Success**.

## Reviewer Token 流程（Dual Channel + Confidential Attachment）

```bash
# 1) 获取审稿任务（免登录）
curl -X GET "http://localhost:8000/api/v1/reviews/token/$REVIEW_TOKEN"

# 2) 提交审稿（免登录）
curl -X POST "http://localhost:8000/api/v1/reviews/token/$REVIEW_TOKEN/submit" \
  -F "content=Public comments to author" \
  -F "score=5" \
  -F "confidential_comments_to_editor=Confidential note to editor" \
  -F "attachment=@/path/to/confidential.pdf"
```

## verifying Privacy

1. Login as Author.
2. Fetch review feedback for your manuscript:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/reviews/feedback/<manuscript_uuid>" \
     -H "Authorization: Bearer $AUTHOR_TOKEN"
   ```
3. Ensure `confidential_comments_to_editor` / `attachment_path` **不出现**（或为 null）。
4. Login as Editor/Admin 再请求同一接口（或在 Dashboard 查看），应能看到机密字段（用于编辑部决策）。
