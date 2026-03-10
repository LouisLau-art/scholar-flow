-- 统一 user_profiles.email 的归一化与唯一性约束

-- 1) 先规范历史数据：lower + trim，空串转 null
update public.user_profiles
set email = nullif(lower(btrim(email)), '')
where email is distinct from nullif(lower(btrim(email)), '');

-- 2) 处理历史重复邮箱：
--    - 优先保留 auth.users 存在的那条 profile
--    - 若都是 orphan，则保留最早一条，其余改成唯一占位邮箱，避免 FK 删除风险
with ranked_profiles as (
  select
    p.id,
    nullif(lower(btrim(p.email)), '') as normalized_email,
    case when au.id is not null then 0 else 1 end as auth_rank,
    row_number() over (
      partition by nullif(lower(btrim(p.email)), '')
      order by
        case when au.id is not null then 0 else 1 end,
        p.created_at asc nulls last,
        p.id asc
    ) as rn
  from public.user_profiles p
  left join auth.users au on au.id = p.id
  where nullif(lower(btrim(p.email)), '') is not null
)
update public.user_profiles p
set
  email = 'dedup+' || replace(p.id::text, '-', '') || '@example.invalid',
  updated_at = now()
from ranked_profiles rp
where p.id = rp.id
  and rp.rn > 1
  and rp.auth_rank = 1;

-- 3) 若仍然存在重复，直接中断迁移，避免静默建索引失败
do $$
declare
  duplicate_count integer;
begin
  select count(*)
  into duplicate_count
  from (
    select email
    from public.user_profiles
    where email is not null
    group by email
    having count(*) > 1
  ) dup;

  if duplicate_count > 0 then
    raise exception 'user_profiles.email still contains % duplicate normalized value(s)', duplicate_count;
  end if;
end $$;

-- 4) 数据库层统一规范化写入
create or replace function public.normalize_user_profile_email()
returns trigger as $$
begin
  if new.email is not null then
    new.email := nullif(lower(btrim(new.email)), '');
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists on_user_profile_email_normalize on public.user_profiles;
create trigger on_user_profile_email_normalize
  before insert or update of email on public.user_profiles
  for each row execute function public.normalize_user_profile_email();

-- 5) auth.users -> user_profiles 邮箱同步也按统一规则写入
create or replace function public.handle_user_email_sync()
returns trigger as $$
begin
  update public.user_profiles
  set email = nullif(lower(btrim(new.email)), ''),
      updated_at = now()
  where id = new.id;
  return new;
end;
$$ language plpgsql security definer;

-- 6) 最终唯一性兜底
drop index if exists public.user_profiles_email_idx;
create unique index if not exists user_profiles_email_unique_idx
  on public.user_profiles (email)
  where email is not null;
