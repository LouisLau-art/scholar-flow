-- Feature: first decision request email template support
-- 1) 允许 email_templates.event_type 使用 first_decision_request
-- 2) 种子一份默认的 first decision 交办邮件模板

alter table public.email_templates
  drop constraint if exists email_templates_event_type_check;

alter table public.email_templates
  add constraint email_templates_event_type_check
  check (event_type in ('none', 'invitation', 'reminder', 'cancellation', 'first_decision_request'));

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
  'first_decision_request_standard',
  '初审决定交办通知（标准）',
  'AE 将稿件送入 First Decision 时，通知学术编辑/主编处理。',
  'decision_workflow',
  'first_decision_request',
  '[{{ journal_title }}] First Decision Request - {{ manuscript_title }}',
  '<p>Dear {{ recipient_name }},</p><p>The manuscript <strong>{{ manuscript_title }}</strong> has been routed to <strong>First Decision</strong>.</p><p>Journal: <strong>{{ journal_title }}</strong><br/>Manuscript ID: <strong>{{ manuscript_id }}</strong><br/>AE Recommendation: <strong>{{ requested_outcome_label }}</strong></p><p>AE Note: {{ ae_note or ''No additional note provided.'' }}</p><p>Open the decision workspace here: <a href="{{ decision_url }}">{{ decision_url }}</a></p><p>Requested by: {{ requested_by_name }}</p>',
  'Dear {{ recipient_name }}, manuscript "{{ manuscript_title }}" (ID: {{ manuscript_id }}) has been routed to First Decision for {{ journal_title }}. AE recommendation: {{ requested_outcome_label }}. AE note: {{ ae_note or ''No additional note provided.'' }}. Decision workspace: {{ decision_url }}. Requested by: {{ requested_by_name }}.',
  true
)
on conflict (template_key) do update
set
  display_name = excluded.display_name,
  description = excluded.description,
  scene = excluded.scene,
  event_type = excluded.event_type,
  subject_template = excluded.subject_template,
  body_html_template = excluded.body_html_template,
  body_text_template = excluded.body_text_template,
  is_active = excluded.is_active,
  updated_at = timezone('utc', now());
