# Quickstart: CMS Feature

## Setup

1. **Install Dependencies**:
   ```bash
   # Frontend
   npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-image isomorphic-dompurify

   # Backend
   pip install -r backend/requirements.txt --break-system-packages
   ```

2. **Database Migration**:
   - 已内置迁移：`supabase/migrations/20260130193000_add_portal_cms.sql`
   - Dev：`supabase db reset`
   - Prod：`supabase db push`

3. **Backend 环境变量（必须）**:
   - `SUPABASE_SERVICE_ROLE_KEY`：用于服务端写入 `cms_pages` / `cms_menu_items` 以及上传 `cms-assets`

## Verification

1. **Start Servers**:
   - Backend: `uvicorn main:app --reload`
   - Frontend: `npm run dev`（或 `pnpm dev`）

2. **Test Flow**:
   - Login as Editor.
   - Go to `Dashboard → Editor → Website`.
   - Create Page "Test", slug "test", content "Hello". Publish.
   - Logout.
   - Visit `/journal/test`. Expect "Hello".
   - Go back to `Website → Menu`，配置 Header/Footer 菜单项（页面或外链），刷新页面后 Header/Footer 应更新。
