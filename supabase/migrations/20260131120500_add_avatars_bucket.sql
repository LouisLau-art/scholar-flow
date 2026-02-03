-- Create avatars storage bucket for Feature 018

-- Create bucket if not exists
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Policies for Avatars
-- 1. Public Read
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Avatar images are public'
    ) THEN
        EXECUTE $policy$
        CREATE POLICY "Avatar images are public"
        ON storage.objects FOR SELECT
        TO public
        USING ( bucket_id = 'avatars' );
        $policy$;
    END IF;
END
$$;

-- 2. Authenticated Upload (User folder isolation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can upload their own avatar'
    ) THEN
        EXECUTE $policy$
        CREATE POLICY "Users can upload their own avatar"
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
        );
        $policy$;
    END IF;
END
$$;

-- 3. Authenticated Update (User folder isolation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can update their own avatar'
    ) THEN
        EXECUTE $policy$
        CREATE POLICY "Users can update their own avatar"
        ON storage.objects FOR UPDATE
        TO authenticated
        USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
        );
        $policy$;
    END IF;
END
$$;

-- 4. Authenticated Delete (User folder isolation - Optional but good hygiene)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Users can delete their own avatar'
    ) THEN
        EXECUTE $policy$
        CREATE POLICY "Users can delete their own avatar"
        ON storage.objects FOR DELETE
        TO authenticated
        USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = auth.uid()::text
        );
        $policy$;
    END IF;
END
$$;
