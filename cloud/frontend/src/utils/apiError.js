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

export function parseApiErrorBody(data, fallbackText = '') {
  if (typeof data === 'object' && data !== null) {
    const message = extractDetailMessage(data.detail)
    if (message) return message
  }
  if (typeof data === 'string' && data) return data
  return fallbackText
}

export function readApiErrorFromBody(data, fallbackText = '') {
  return parseApiErrorBody(data, fallbackText || i18n.global.t('common.unknownError'))
}

export async function readApiError(response) {
  const text = await response.text()
  try {
    const data = JSON.parse(text)
    return readApiErrorFromBody(data, text || response.statusText)
  } catch {
    return text || response.statusText || i18n.global.t('common.unknownError')
  }
}

/** @deprecated Use readApiError(response) or parseApiErrorBody(data). */
export async function parseApiErrorDetail(response) {
  return readApiError(response)
}
