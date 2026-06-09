function extractDetailMessage(detail) {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message
    return JSON.stringify(detail)
  }
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => (entry && typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry)))
      .join('; ')
  }
  return null
}

export function parseApiErrorDetail(data, fallbackText = '') {
  if (typeof data === 'object' && data !== null) {
    const message = extractDetailMessage(data.detail)
    if (message) return message
  }
  if (typeof data === 'string' && data) return data
  return fallbackText
}

export async function readApiError(response) {
  const text = await response.text()
  try {
    const data = JSON.parse(text)
    return parseApiErrorDetail(data, text || response.statusText)
  } catch {
    return text || response.statusText
  }
}
