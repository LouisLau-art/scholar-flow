-- Feature 026: Automated Invoice PDF - Storage bucket
-- 目标：创建私有 invoices bucket，PDF 下载走后端 signed URL（鉴权后下发）

insert into storage.buckets (id, name, public)
values ('invoices', 'invoices', false)
on conflict (id) do nothing;

