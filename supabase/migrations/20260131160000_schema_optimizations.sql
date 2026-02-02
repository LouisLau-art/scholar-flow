-- ScholarFlow Schema 深度优化脚本 (2026-01-31)

-- 1. 数据清理与字段合并 (user_profiles)
-- 迁移数据：将旧字段的数据备份到新字段（仅当新字段为空时）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'user_profiles'
          AND column_name = 'name'
    ) THEN
        EXECUTE 'UPDATE public.user_profiles SET full_name = name WHERE full_name IS NULL AND name IS NOT NULL;';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'user_profiles'
          AND column_name = 'institution'
    ) THEN
        EXECUTE 'UPDATE public.user_profiles SET affiliation = institution WHERE affiliation IS NULL AND institution IS NOT NULL;';
    END IF;
END
$$;

-- 强制统一 research_interests 类型为 text[] (处理从文本转数组的逻辑)
DO $$
BEGIN
    IF (SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'user_profiles' AND column_name = 'research_interests' AND table_schema = 'public') = 'text' THEN
        ALTER TABLE public.user_profiles 
        ALTER COLUMN research_interests TYPE text[] 
        USING ARRAY[research_interests];
    END IF;
END $$;

-- 删除冗余旧字段
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS name;
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS institution;

-- 2. 性能优化：添加全文检索索引 (Manuscripts)
-- 中文注释: 使用 GIN 索引提升对标题和摘要的关键词检索速度
CREATE INDEX IF NOT EXISTS idx_manuscripts_fulltext_search 
ON public.manuscripts USING GIN (to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(abstract, '')));

-- 3. 增强审计支持：软删除字段
ALTER TABLE public.manuscripts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.review_reports ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 4. 自动化：Auth 邮箱同步触发器
-- 当用户在 Supabase Auth 修改邮箱时，自动同步到 public.user_profiles
CREATE OR REPLACE FUNCTION public.handle_user_email_sync()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.user_profiles
  SET email = new.email,
      updated_at = now()
  WHERE id = new.id;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 绑定触发器到 auth.users 表
DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_user_email_sync();

-- 5. 补充：为稿件列表增加默认排序索引
CREATE INDEX IF NOT EXISTS idx_manuscripts_created_at_desc ON public.manuscripts(created_at DESC);
