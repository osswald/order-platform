/** Helpers for event Lager price overrides (org price + optional event price). */

/** Map an Eventpreis input to the API override field: empty clears (null). */
export function eventPriceOverrideForSave(
  value: number | string | null | undefined,
): number | null {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) {
    return null
  }
  return n
}

/** Local stock row fields derived from event-stock API item. */
export function stockItemPriceFields(row: {
  org_price?: number | null
  price?: number | null
}): { org_price: number; price: number | null } {
  return {
    org_price: Number(row.org_price ?? 0),
    price: row.price == null ? null : Number(row.price),
  }
}
