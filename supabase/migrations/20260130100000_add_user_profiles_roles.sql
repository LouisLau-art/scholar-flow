-- Create a minimal user profile/role table for the app layer.
-- Note: this project currently uses the Supabase anon key from the backend,
-- so we keep the schema simple and enforce permissions at the API layer.

create table if not exists public.user_profiles (
  id uuid primary key,
  email text,
  roles text[] not null default array['author'],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists user_profiles_email_idx on public.user_profiles (email);

