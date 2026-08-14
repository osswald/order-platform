/** Customer display success / pickup helpers (pure). */

export function pickupCodesForDisplay(payload: {
  pickup_codes?: string[] | null
  pickup_code?: string | null
}): string[] {
  const codes = (payload.pickup_codes || []).map(String).filter(Boolean)
  if (codes.length) return codes
  const single = payload.pickup_code != null ? String(payload.pickup_code).trim() : ''
  return single ? [single] : []
}

export function abholbonFooterText(codeCount: number): string {
  if (codeCount >= 2) return 'Bitte Abholbons mitnehmen'
  return 'Bitte Abholbon mitnehmen'
}
