/** Client-side validation for the Mietanfrage form (pure, testable). */

export function validateInquiryFields(fields) {
  const required = ['name', 'organisation', 'email', 'timeframe', 'message']
  for (const key of required) {
    if (!String(fields[key] ?? '').trim()) {
      return 'Bitte füllen Sie alle Pflichtfelder aus.'
    }
  }
  const email = String(fields.email || '').trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return 'Bitte geben Sie eine gültige E-Mail-Adresse ein.'
  }
  return null
}
