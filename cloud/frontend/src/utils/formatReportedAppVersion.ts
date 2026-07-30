/** Format reported Pi backend app version for the cloud SD-card table. */
export function formatReportedAppVersion(
  version: string | null | undefined,
  buildTime?: string | null,
  emptyLabel = '—',
): string {
  const trimmed = version?.trim()
  if (!trimmed) return emptyLabel
  const base = `v${trimmed}`
  if (buildTime && buildTime !== 'dev') {
    return `${base} (${buildTime})`
  }
  return base
}
