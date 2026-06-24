import { i18n } from '@/i18n'

function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const record = detail as Record<string, unknown>
    if (typeof record.message === 'string') return record.message
    if (typeof record.code === 'string') {
      const translated = i18n.global.t(`errors.${record.code}`)
      if (translated !== `errors.${record.code}`) return translated
    }
    return JSON.stringify(detail)
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) =>
        entry && typeof entry === 'object' && typeof (entry as { msg?: unknown }).msg === 'string'
          ? (entry as { msg: string }).msg
          : JSON.stringify(entry),
      )
      .join('; ')
  }
  return null
}

export function parseApiErrorBody(data: unknown, fallbackText = ''): string {
  if (typeof data === 'object' && data !== null) {
    const record = data as { detail?: unknown }
    const message = extractDetailMessage(record.detail)
    if (message) return message
  }
  if (typeof data === 'string' && data) return data
  return fallbackText
}

export function readApiErrorFromBody(data: unknown, fallbackText = ''): string {
  return parseApiErrorBody(data, fallbackText || i18n.global.t('common.unknownError'))
}

export async function readApiError(response: Response): Promise<string> {
  const text = await response.text()
  try {
    const data = JSON.parse(text) as unknown
    return readApiErrorFromBody(data, text || response.statusText)
  } catch {
    return text || response.statusText || i18n.global.t('common.unknownError')
  }
}

/** @deprecated Use readApiError(response) or parseApiErrorBody(data). */
export async function parseApiErrorDetail(response: Response): Promise<string> {
  return readApiError(response)
}
