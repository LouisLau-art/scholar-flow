alter table if exists public.manuscripts
  add column if not exists dataset_url text,
  add column if not exists source_code_url text;
