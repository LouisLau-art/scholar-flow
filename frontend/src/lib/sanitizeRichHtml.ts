const BLOCKED_TAGS = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'link',
  'meta',
  'form',
  'input',
  'button',
  'textarea',
  'select',
])

const URL_ATTRS = new Set(['href', 'src', 'xlink:href', 'formaction'])

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function hasSafeProtocol(url: URL): boolean {
  return ['http:', 'https:', 'mailto:', 'tel:'].includes(url.protocol)
}

function isAllowedDataImage(value: string): boolean {
  return /^data:image\/(?:png|jpe?g|gif|webp|svg\+xml);base64,[a-z0-9+/=]+$/i.test(value)
}

function isSafeUrl(value: string, tagName: string, attrName: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) return true
  if (trimmed.startsWith('#') || trimmed.startsWith('/')) return true

  if (tagName === 'img' && attrName === 'src' && isAllowedDataImage(trimmed)) {
    return true
  }

  try {
    const parsed = new URL(trimmed, window.location.origin)
    return hasSafeProtocol(parsed)
  } catch {
    return false
  }
}

export function sanitizeRichHtml(raw: string): string {
  if (!raw) return ''
  if (typeof window === 'undefined') {
    return escapeHtml(raw)
  }

  const template = document.createElement('template')
  template.innerHTML = raw

  const nodes = Array.from(template.content.querySelectorAll('*'))
  for (const node of nodes) {
    const tagName = node.tagName.toLowerCase()
    if (BLOCKED_TAGS.has(tagName)) {
      node.remove()
      continue
    }

    const attrs = Array.from(node.attributes)
    for (const attr of attrs) {
      const attrName = attr.name.toLowerCase()
      const attrValue = attr.value

      if (attrName.startsWith('on') || attrName === 'style' || attrName === 'srcset') {
        node.removeAttribute(attr.name)
        continue
      }

      if (URL_ATTRS.has(attrName) && !isSafeUrl(attrValue, tagName, attrName)) {
        node.removeAttribute(attr.name)
      }
    }

    if (tagName === 'a' && node.hasAttribute('href')) {
      node.setAttribute('rel', 'noopener noreferrer nofollow')
      if (!node.getAttribute('target')) {
        node.setAttribute('target', '_blank')
      }
    }
  }

  return template.innerHTML
}
