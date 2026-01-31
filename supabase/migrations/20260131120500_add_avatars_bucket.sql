-- Create avatars storage bucket for Feature 018

-- Create bucket if not exists
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Policies for Avatars
-- 1. Public Read
CREATE POLICY "Avatar images are public"
ON storage.objects FOR SELECT
TO public
USING ( bucket_id = 'avatars' );

-- 2. Authenticated Upload (User folder isolation)
CREATE POLICY "Users can upload their own avatar"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 3. Authenticated Update (User folder isolation)
CREATE POLICY "Users can update their own avatar"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 4. Authenticated Delete (User folder isolation - Optional but good hygiene)
CREATE POLICY "Users can delete their own avatar"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);
