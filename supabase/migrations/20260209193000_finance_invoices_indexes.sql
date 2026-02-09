-- Feature 046: Finance Invoices Sync
-- 目标：优化 Finance 列表的状态筛选与时间排序查询。

create index if not exists invoices_status_confirmed_at_idx
on public.invoices (status, confirmed_at desc);

create index if not exists invoices_created_at_idx
on public.invoices (created_at desc);
