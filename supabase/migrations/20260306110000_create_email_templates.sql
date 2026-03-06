-- Feature 048: Email Template Management (Admin)
-- 目标：
-- 1) 提供跨刊物可复用的邮件模板库（不再硬编码 invitation/reminder）
-- 2) 支持模板变量渲染（例如 {{ journal_title }}）
-- 3) 支持 reviewer assignment 场景的事件回填（invitation/reminder）

create table if not exists public.email_templates (
  id uuid primary key default gen_random_uuid(),
  template_key text not null unique,
  display_name text not null,
  description text,
  scene text not null default 'general',
  event_type text not null default 'none'
    constraint email_templates_event_type_check check (event_type in ('none', 'invitation', 'reminder')),
  subject_template text not null,
  body_html_template text not null,
  body_text_template text,
  is_active boolean not null default true,
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint email_templates_template_key_format_check
    check (template_key ~ '^[a-z0-9_]{2,64}$'),
  constraint email_templates_scene_format_check
    check (scene ~ '^[a-z0-9_]{2,64}$'),
  constraint email_templates_display_name_len_check
    check (char_length(trim(display_name)) between 2 and 120),
  constraint email_templates_subject_len_check
    check (char_length(trim(subject_template)) between 1 and 500),
  constraint email_templates_html_len_check
    check (char_length(trim(body_html_template)) between 1 and 50000)
);

create index if not exists idx_email_templates_scene_active
  on public.email_templates(scene, is_active);

create index if not exists idx_email_templates_updated_at
  on public.email_templates(updated_at desc);

create or replace function public.set_email_templates_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_set_email_templates_updated_at on public.email_templates;
create trigger trg_set_email_templates_updated_at
before update on public.email_templates
for each row
execute function public.set_email_templates_updated_at();

insert into public.email_templates (
  template_key,
  display_name,
  description,
  scene,
  event_type,
  subject_template,
  body_html_template,
  body_text_template,
  is_active
)
values
  (
    'reviewer_invitation_standard',
    '审稿邀请信（标准）',
    '默认审稿邀请模板，包含 magic link 与期刊名。',
    'reviewer_assignment',
    'invitation',
    'Invitation to Review - {{ journal_title }}',
    '<p>Dear {{ reviewer_name }},</p><p>You are invited to review the manuscript <strong>{{ manuscript_title }}</strong> for <strong>{{ journal_title }}</strong>.</p><p>Due date: {{ due_date or due_at or ''-'' }}</p><p>Please open your invitation here: <a href="{{ review_url }}">{{ review_url }}</a></p><p>Best regards,<br/>{{ journal_title }} Editorial Office</p>',
    'Dear {{ reviewer_name }}, You are invited to review "{{ manuscript_title }}" for {{ journal_title }}. Due: {{ due_date or due_at or ''-'' }}. Link: {{ review_url }}',
    true
  ),
  (
    'reviewer_invitation_formal',
    '审稿邀请信（正式）',
    '偏正式语气版本的审稿邀请信。',
    'reviewer_assignment',
    'invitation',
    '[{{ journal_title }}] Review Invitation: {{ manuscript_title }}',
    '<p>Dear {{ reviewer_name }},</p><p>On behalf of <strong>{{ journal_title }}</strong>, we sincerely invite you to review the manuscript titled <strong>{{ manuscript_title }}</strong> (ID: {{ manuscript_id }}).</p><p>Requested due date: {{ due_date or due_at or ''-'' }}.</p><p>Please access the invitation link: <a href="{{ review_url }}">{{ review_url }}</a></p><p>Thank you for your contribution.</p>',
    'Dear {{ reviewer_name }}, {{ journal_title }} invites you to review "{{ manuscript_title }}" ({{ manuscript_id }}). Due: {{ due_date or due_at or ''-'' }}. Link: {{ review_url }}',
    true
  ),
  (
    'reviewer_reminder_polite',
    '审稿催促信（礼貌）',
    '用于外审中温和提醒审稿人。',
    'reviewer_assignment',
    'reminder',
    'Friendly Reminder - {{ journal_title }} Review for {{ manuscript_title }}',
    '<p>Dear {{ reviewer_name }},</p><p>This is a gentle reminder for your review of <strong>{{ manuscript_title }}</strong> ({{ journal_title }}).</p><p>Current due date: {{ due_date or due_at or ''-'' }}.</p><p>You can continue via: <a href="{{ review_url }}">{{ review_url }}</a></p><p>Many thanks.</p>',
    'Dear {{ reviewer_name }}, this is a reminder for your review of "{{ manuscript_title }}" ({{ journal_title }}). Due: {{ due_date or due_at or ''-'' }}. Link: {{ review_url }}',
    true
  ),
  (
    'reviewer_reminder_urgent',
    '审稿催促信（紧急）',
    '用于接近截止日期时提醒审稿人。',
    'reviewer_assignment',
    'reminder',
    '[Urgent] Review Deadline Approaching - {{ journal_title }}',
    '<p>Dear {{ reviewer_name }},</p><p>Your review for <strong>{{ manuscript_title }}</strong> is approaching the deadline.</p><p>Journal: <strong>{{ journal_title }}</strong><br/>Due date: {{ due_date or due_at or ''-'' }}</p><p>Please submit your feedback as soon as possible: <a href="{{ review_url }}">{{ review_url }}</a></p>',
    'Urgent reminder: review for "{{ manuscript_title }}" ({{ journal_title }}) is due on {{ due_date or due_at or ''-'' }}. Link: {{ review_url }}',
    true
  ),
  (
    'author_submission_received',
    '作者投稿确认信',
    '作者提交稿件后发送确认邮件。',
    'author_notification',
    'none',
    '[{{ journal_title }}] Submission Received: {{ manuscript_title }}',
    '<p>Dear {{ author_name }},</p><p>We have received your submission <strong>{{ manuscript_title }}</strong> in <strong>{{ journal_title }}</strong>.</p><p>Manuscript ID: {{ manuscript_id }}</p><p>We will keep you updated on progress.</p>',
    'Dear {{ author_name }}, we have received your submission "{{ manuscript_title }}" ({{ manuscript_id }}) in {{ journal_title }}.',
    true
  ),
  (
    'decision_accept_basic',
    '录用通知（基础）',
    '决策为录用时的基础通知模板。',
    'decision',
    'none',
    '[{{ journal_title }}] Decision: Accept - {{ manuscript_title }}',
    '<p>Dear {{ author_name }},</p><p>We are pleased to inform you that your manuscript <strong>{{ manuscript_title }}</strong> has been accepted by <strong>{{ journal_title }}</strong>.</p><p>Thank you for your contribution.</p>',
    'Dear {{ author_name }}, your manuscript "{{ manuscript_title }}" has been accepted by {{ journal_title }}.',
    true
  )
on conflict (template_key) do update set
  display_name = excluded.display_name,
  description = excluded.description,
  scene = excluded.scene,
  event_type = excluded.event_type,
  subject_template = excluded.subject_template,
  body_html_template = excluded.body_html_template,
  body_text_template = excluded.body_text_template,
  is_active = excluded.is_active,
  updated_at = now();
