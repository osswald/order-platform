/** Copy catalog name into receipt label when label is still empty (max 21 chars). */
export function labelFromNameIfEmpty(name: string, label: string): string {
  if (String(label || '').trim()) {
    return label
  }
  return String(name || '').trim().slice(0, 21)
}
