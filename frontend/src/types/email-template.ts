export type EmailTemplateEventType = 'none' | 'invitation' | 'reminder' | 'cancellation'

export type EmailTemplate = {
  id: string
  template_key: string
  display_name: string
  description?: string | null
  scene: string
  event_type: EmailTemplateEventType
  subject_template: string
  body_html_template: string
  body_text_template?: string | null
  is_active: boolean
  updated_by?: string | null
  created_at: string
  updated_at: string
}

export type EmailTemplateCreatePayload = {
  template_key: string
  display_name: string
  description?: string | null
  scene: string
  event_type: EmailTemplateEventType
  subject_template: string
  body_html_template: string
  body_text_template?: string | null
  is_active: boolean
}

export type EmailTemplateUpdatePayload = Partial<EmailTemplateCreatePayload>

export type ReviewEmailTemplateOption = {
  template_key: string
  display_name: string
  description?: string | null
  scene: string
  event_type: EmailTemplateEventType
}
