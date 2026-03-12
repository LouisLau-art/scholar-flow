-- Allow LaTeX ZIP source archives in manuscript_files taxonomy.
-- This keeps author submission ZIP uploads compatible with the existing
-- manuscript_files metadata table instead of overloading `manuscript`.

alter table public.manuscript_files
  drop constraint if exists manuscript_files_file_type_check;

alter table public.manuscript_files
  add constraint manuscript_files_file_type_check
  check (
    file_type in (
      'cover_letter',
      'manuscript',
      'review_attachment',
      'source_archive'
    )
  );

comment on column public.manuscript_files.file_type is
  'cover_letter | manuscript | review_attachment | source_archive';

select pg_notify('pgrst', 'reload schema');
