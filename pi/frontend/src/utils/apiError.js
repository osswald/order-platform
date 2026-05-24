export function parseApiErrorDetail(data, fallbackText = '') {
  if (typeof data === 'object' && data !== null) {
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((entry) => (entry && typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry)))
        .join('; ')
    }
    if (data.detail) return JSON.stringify(data.detail)
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
