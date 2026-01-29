-- Create manuscripts bucket and RLS policies for owner access

insert into storage.buckets (id, name, public)
values ('manuscripts', 'manuscripts', false)
on conflict (id) do nothing;

-- Ensure clean policy definitions
DROP POLICY IF EXISTS "manuscripts_owner_select" ON storage.objects;
DROP POLICY IF EXISTS "manuscripts_owner_insert" ON storage.objects;
DROP POLICY IF EXISTS "manuscripts_owner_update" ON storage.objects;
DROP POLICY IF EXISTS "manuscripts_owner_delete" ON storage.objects;

CREATE POLICY "manuscripts_owner_select"
ON storage.objects
FOR SELECT
USING (
  bucket_id = 'manuscripts'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "manuscripts_owner_insert"
ON storage.objects
FOR INSERT
WITH CHECK (
  bucket_id = 'manuscripts'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "manuscripts_owner_update"
ON storage.objects
FOR UPDATE
USING (
  bucket_id = 'manuscripts'
  AND auth.uid()::text = (storage.foldername(name))[1]
)
WITH CHECK (
  bucket_id = 'manuscripts'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "manuscripts_owner_delete"
ON storage.objects
FOR DELETE
USING (
  bucket_id = 'manuscripts'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
