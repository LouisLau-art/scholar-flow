-- Feature 033: Align Detail Page Layout
-- Purpose:
-- - Store editor/internal files attached to a manuscript with a simple file_type taxonomy.
-- - MVP scope focuses on `review_attachment` (peer review files uploaded by editor/admin).

create table if not exists public.manuscript_files (
  id uuid primary key default gen_random_uuid(),
  manuscript_id uuid not null references public.manuscripts(id) on delete cascade,
  file_type text not null check (file_type in ('cover_letter', 'manuscript', 'review_attachment')),
  bucket text not null,
  path text not null,
  original_filename text,
  content_type text,
  uploaded_by uuid references public.user_profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists manuscript_files_manuscript_id_idx on public.manuscript_files (manuscript_id);
create index if not exists manuscript_files_file_type_idx on public.manuscript_files (file_type);
create unique index if not exists manuscript_files_bucket_path_uniq on public.manuscript_files (bucket, path);

comment on table public.manuscript_files is 'Internal manuscript files (Feature 033). Editor-only in MVP; access controlled by API.';
comment on column public.manuscript_files.file_type is 'cover_letter | manuscript | review_attachment';
comment on column public.manuscript_files.bucket is 'Supabase Storage bucket name';
comment on column public.manuscript_files.path is 'Object path within bucket';
