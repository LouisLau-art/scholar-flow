-- Function to truncate all tables (Used by Seed Script)
create or replace function public.truncate_all_tables()
returns void
language plpgsql
security definer
as $$
declare
    r record;
begin
    -- Disable triggers to prevent FK issues during mass truncate
    -- Note: This requires superuser or replica role, or we iterate carefully.
    -- Better approach for Supabase: Iterate and TRUNCATE CASCADE.
    
    for r in (select tablename from pg_tables where schemaname = 'public') loop
        execute 'truncate table public.' || quote_ident(r.tablename) || ' cascade';
    end loop;
end;
$$;
