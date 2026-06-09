import { i18n } from '../i18n'

function extractDetailMessage(detail) {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message
    if (typeof detail.code === 'string') {
      const translated = i18n.global.t(`errors.${detail.code}`)
      if (translated !== `errors.${detail.code}`) return translated
    }
    return JSON.stringify(detail)
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => (entry && typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry)))
      .join('; ')
  }
  return null
}

export async function parseApiErrorDetail(response) {
  const text = await response.text()
  try {
    const data = JSON.parse(text)
    const message = extractDetailMessage(data.detail)
    if (message) return message
  } catch {
    // not JSON
  }
  return text || i18n.global.t('common.unknownError')
}
