# Quickstart: CMS Feature

## Setup

1. **Install Dependencies**:
   ```bash
   # Frontend
   npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-image isomorphic-dompurify

   # Backend
   # (Add to requirements.txt)
   bleach
   ```

2. **Database Migration**:
   - Run `supabase migration new cms_tables`
   - Paste content from `data-model.md` logic (create tables + RLS).
   - Apply: `supabase db reset` (dev) or push.

3. **Storage Bucket**:
   - Create public bucket `cms-assets`.
   - Policy: Public Read, Authenticated Insert (Editor only).

## Verification

1. **Start Servers**:
   - Backend: `uvicorn main:app --reload`
   - Frontend: `npm run dev`

2. **Test Flow**:
   - Login as Editor.
   - Go to `/editor/cms`.
   - Create Page "Test", slug "test", content "Hello". Publish.
   - Logout.
   - Visit `/journal/test`. Expect "Hello".
