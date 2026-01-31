# Quickstart: Feature 018

## Prerequisites

1.  **Storage Bucket**:
    Run this SQL in Supabase Dashboard to create the `avatars` bucket and policies:

    ```sql
    -- Create bucket
    insert into storage.buckets (id, name, public)
    values ('avatars', 'avatars', true);

    -- Policy: Authenticated users can upload their own avatar
    create policy "Users can upload their own avatar"
    on storage.objects for insert
    to authenticated
    with check ( bucket_id = 'avatars' and auth.uid()::text = (storage.foldername(name))[1] );

    -- Policy: Authenticated users can update their own avatar
    create policy "Users can update their own avatar"
    on storage.objects for update
    to authenticated
    using ( bucket_id = 'avatars' and auth.uid()::text = (storage.foldername(name))[1] );

    -- Policy: Public Read
    create policy "Avatar images are public"
    on storage.objects for select
    to public
    using ( bucket_id = 'avatars' );
    ```

2.  **Database Migration**:
    Run the migration script (to be created) to add `research_interests`, `orcid_id`, etc., to `public.profiles`.

## Testing

1.  **Frontend**:
    - Go to `/settings` (or click Avatar -> Settings).
    - Try uploading an image > 2MB (Should fail).
    - Try uploading a valid image.
    - Change name and save. Check Navbar.

2.  **Backend**:
    - `pytest tests/integration/test_user_profile.py`
