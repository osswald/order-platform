/** Parse API ISO timestamp; timezone-less strings are treated as UTC. */
export function parseApiDate(iso) {
  if (!iso) return null
  let s = String(iso).trim()
  if (!s) return null
  if (!s.endsWith('Z') && !/[+-]\d{2}:?\d{2}$/.test(s)) {
    s = `${s}Z`
  }
  const ts = new Date(s)
  return Number.isNaN(ts.getTime()) ? null : ts
}

/** Format ISO timestamp for Swiss locale display. */
export function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    const ts = parseApiDate(iso)
    if (!ts) return iso
    return ts.toLocaleString('de-CH')
  } catch {
    return iso
  }
}
