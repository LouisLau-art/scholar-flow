const SCRIPT_STYLE_RE = /<(script|style)[^>]*>[\s\S]*?<\/\1>/gi
const HTML_LINK_RE = /<a\b[^>]*href=['"]?([^'">\s]+)[^>]*>([\s\S]*?)<\/a>/gi
const HTML_BREAK_RE = /<br\s*\/?>/gi
const HTML_PARAGRAPH_CLOSE_RE = /<\/(p|div|h[1-6]|section|article)>/gi
const HTML_BLOCK_CLOSE_RE = /<\/(li|ul|ol|tr|table)>/gi
const HTML_LIST_OPEN_RE = /<li\b[^>]*>/gi
const HTML_TAG_RE = /<[^>]+>/g

function decodeHtmlEntities(value: string): string {
  if (typeof document === 'undefined') return value
  const textarea = document.createElement('textarea')
  textarea.innerHTML = value
  return textarea.value
}

export function derivePlainTextFromHtml(html: string): string {
  const replaceLink = (_match: string, hrefRaw: string, innerHtml: string) => {
    const href = decodeHtmlEntities(String(hrefRaw || '').trim())
    const innerText = decodeHtmlEntities(String(innerHtml || '').replace(HTML_TAG_RE, ' ').replace(/\s+/g, ' ').trim())
    if (innerText && href) {
      return innerText === href ? innerText : `${innerText} (${href})`
    }
    return innerText || href
  }

  let cleaned = String(html || '')
  cleaned = cleaned.replace(SCRIPT_STYLE_RE, ' ')
  cleaned = cleaned.replace(HTML_LINK_RE, replaceLink)
  cleaned = cleaned.replace(HTML_BREAK_RE, '\n')
  cleaned = cleaned.replace(HTML_PARAGRAPH_CLOSE_RE, '\n\n')
  cleaned = cleaned.replace(HTML_BLOCK_CLOSE_RE, '\n')
  cleaned = cleaned.replace(HTML_LIST_OPEN_RE, '- ')
  cleaned = cleaned.replace(HTML_TAG_RE, ' ')
  cleaned = decodeHtmlEntities(cleaned)
  cleaned = cleaned.replace(/\r/g, '')
  cleaned = cleaned.replace(/[ \t\f\v]+/g, ' ')
  cleaned = cleaned.replace(/ *\n */g, '\n')
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim()
  return cleaned
}
