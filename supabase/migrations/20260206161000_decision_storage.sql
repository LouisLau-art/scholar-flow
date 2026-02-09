-- Feature 041: decision attachments storage bucket
-- 说明：保持私有桶，访问统一走后端 signed URL

insert into storage.buckets (id, name, public)
values ('decision-attachments', 'decision-attachments', false)
on conflict (id) do nothing;
