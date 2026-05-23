const amountFormatter = new Intl.NumberFormat('de-CH', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Amount in major units from cents, Swiss format without currency symbol. */
export function formatAmount(cents) {
  return amountFormatter.format((cents || 0) / 100)
}
