export async function parseApiErrorDetail(response) {
  const text = await response.text()
  try {
    const data = JSON.parse(text)
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((entry) => (entry && typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry)))
        .join('; ')
    }
  } catch {
    // not JSON
  }
  return text || 'Unbekannter Fehler'
}
