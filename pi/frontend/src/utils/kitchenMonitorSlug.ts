export interface KitchenMonitorPrinterRef {
  printer_appliance_id: number
  label: string
  sort_order?: number
}

export function slugifyKitchenMonitorLabel(label: string): string {
  const normalized = String(label || '')
    .trim()
    .toLowerCase()
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return normalized || 'station'
}

export function assignKitchenMonitorSlugs(
  printers: KitchenMonitorPrinterRef[],
): Map<number, string> {
  const used = new Set<string>()
  const out = new Map<number, string>()
  for (const printer of printers) {
    const base = slugifyKitchenMonitorLabel(printer.label) || `drucker-${printer.printer_appliance_id}`
    let slug = base
    if (used.has(slug)) slug = `${base}-${printer.printer_appliance_id}`
    used.add(slug)
    out.set(printer.printer_appliance_id, slug)
  }
  return out
}

export function kitchenMonitorPrinterBySlug(
  slug: string,
  printers: KitchenMonitorPrinterRef[],
): KitchenMonitorPrinterRef | null {
  const target = String(slug || '').trim().toLowerCase()
  if (!target) return null
  const slugMap = assignKitchenMonitorSlugs(printers)
  for (const printer of printers) {
    if (slugMap.get(printer.printer_appliance_id) === target) return printer
  }
  return null
}
