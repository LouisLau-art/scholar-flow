-- Create UAT Feedback table
create table if not exists public.uat_feedback (
    id uuid default gen_random_uuid() primary key,
    description text not null check (length(description) >= 5),
    severity varchar(20) not null check (severity in ('low', 'medium', 'critical')),
    url text not null,
    user_id uuid references auth.users(id),
    status varchar(20) default 'new' check (status in ('new', 'triaged', 'resolved', 'ignored')),
    created_at timestamptz default now() not null
);

-- Enable RLS
alter table public.uat_feedback enable row level security;

-- Policies
-- 1. Anyone (anon/authenticated) can insert feedback
create policy "Anyone can insert feedback"
    on public.uat_feedback
    for insert
    with check (true);

-- 2. Only admins can view feedback (assuming admin role check logic exists or just basic authenticated for now)
-- Ideally: auth.uid() in (select user_id from user_roles where role = 'admin')
-- For MVP UAT: Authenticated users (Editors/Admins) can view.
create policy "Authenticated users can view feedback"
    on public.uat_feedback
    for select
    to authenticated
    using (true);
