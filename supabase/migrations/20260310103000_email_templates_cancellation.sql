-- Feature 0xx: reviewer cancellation email template + event type
-- 目标：
-- 1) 允许 email_templates.event_type 使用 cancellation
-- 2) 为 reviewer assignment 场景补默认取消通知模板

alter table public.email_templates
  drop constraint if exists email_templates_event_type_check;

alter table public.email_templates
  add constraint email_templates_event_type_check
  check (event_type in ('none', 'invitation', 'reminder', 'cancellation'));

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
values (
  'reviewer_cancellation_standard',
  '审稿取消通知（标准）',
  '当编辑部结束当前 reviewer assignment 时发送取消通知。',
  'reviewer_assignment',
  'cancellation',
  'Review Assignment Cancelled - {{ journal_title }}',
  '<p>Dear {{ reviewer_name }},</p><p>Your review assignment for <strong>{{ manuscript_title }}</strong> in <strong>{{ journal_title }}</strong> has been cancelled.</p><p>Manuscript ID: {{ manuscript_id }}</p><p>Reason: {{ cancel_reason or ''Editorial workflow updated.'' }}</p><p>No further action is required. If you already started reviewing, please disregard the earlier invitation link.</p><p>Thank you for your time and support.</p>',
  'Dear {{ reviewer_name }}, your review assignment for "{{ manuscript_title }}" in {{ journal_title }} has been cancelled. Manuscript ID: {{ manuscript_id }}. Reason: {{ cancel_reason or ''Editorial workflow updated.'' }}. No further action is required.',
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
