-- Feature 026: Automated Invoice PDF - invoice metadata fields
-- 目标：为 invoices 增加“可持久化 PDF + 可重试”的字段（不保存短期 signed URL）

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS invoice_number TEXT;

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS pdf_path TEXT;

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS pdf_generated_at TIMESTAMPTZ;

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS pdf_error TEXT;

-- 常用查询索引：按稿件找 invoice、以及按 pdf_path 判定是否已生成
CREATE INDEX IF NOT EXISTS invoices_manuscript_id_idx
  ON public.invoices (manuscript_id);

CREATE INDEX IF NOT EXISTS invoices_pdf_path_idx
  ON public.invoices (pdf_path);

