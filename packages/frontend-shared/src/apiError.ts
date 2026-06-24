function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const obj = detail as Record<string, unknown>
    if (typeof obj.message === 'string') return obj.message
    return JSON.stringify(detail)
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) =>
        entry && typeof entry === 'object' && typeof (entry as { msg?: string }).msg === 'string'
          ? (entry as { msg: string }).msg
          : JSON.stringify(entry),
      )
      .join('; ')
  }
  return null
}

export function parseApiErrorDetail(data: unknown, fallbackText = ''): string {
  if (typeof data === 'object' && data !== null) {
    const message = extractDetailMessage((data as { detail?: unknown }).detail)
    if (message) return message
  }
  if (typeof data === 'string' && data) return data
  return fallbackText
}

export async function readApiError(response: Response): Promise<string> {
  const text = await response.text()
  try {
    const data = JSON.parse(text) as unknown
    return parseApiErrorDetail(data, text || response.statusText)
  } catch {
    return text || response.statusText
  }
}
