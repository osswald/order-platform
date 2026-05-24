/** Format ISO timestamp for Swiss locale display. */
export function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}
