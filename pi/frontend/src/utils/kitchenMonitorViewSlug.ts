export type KitchenMonitorViewMode = 'orders' | 'products'

export function kitchenViewModeFromSlug(slug: string | undefined | null): KitchenMonitorViewMode {
  return String(slug || '').toLowerCase() === 'produkte' ? 'products' : 'orders'
}

export function kitchenViewSlugFromMode(mode: KitchenMonitorViewMode): string {
  return mode === 'products' ? 'produkte' : 'bestellungen'
}
