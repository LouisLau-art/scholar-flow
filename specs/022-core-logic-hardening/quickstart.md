# Quickstart: Core Logic Hardening

## Prerequisites

- Python 环境可用（Backend 可启动/可跑集成测试）
- Supabase：默认使用**云端 Supabase**（推荐用 Supabase CLI 同步 migration）

## Database Setup

1. Run the migration to add dual comment fields:
   ```bash
   # 在 repo root
   supabase db push --dry-run
   supabase db push
   ```

## Testing the Financial Gate

1. **Submit** a manuscript (Author).
2. **Review** it (Reviewer) - try adding confidential comments.
3. **Accept** it (Editor) - **Set APC > 0** in the dialog.
4. **Try to Publish** (Editor) - **Expect Failure (403)**.
   ```bash
   curl -X POST http://localhost:8000/api/v1/editor/publish ...
   ```
5. **Simulate Payment**:
   - Manually update `invoices` table:
     `UPDATE invoices SET status = 'paid', confirmed_at = now() WHERE manuscript_id = '...'`
6. **Try to Publish** (Editor) - **Expect Success**.

## verifying Privacy

1. Login as Author.
2. Fetch review reports for your manuscript.
3. Ensure `confidential_comments_to_editor` is MISSING or null.
