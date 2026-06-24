const ADDITIONS_KEY = 'additions'
const ADDITIONS_NAME = 'Zusätze'

interface StockRow {
  id?: number
  name?: string
  monitor_stock?: boolean
}

interface StationLike {
  uuid?: string
  name?: string
  sort_order?: number
  article_ids?: number[]
}

export interface StockGroup {
  key: string
  name: string
  items: StockRow[]
}

function sortByName(a: StockRow, b: StockRow): number {
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'de')
}

function sortedStations(stations: StationLike[] | undefined): StationLike[] {
  return (stations || [])
    .slice()
    .sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0))
}

function articleListFromEvent(
  ev: { articles?: Record<string, StockRow> } | null | undefined,
  monitoredOnly: boolean,
): StockRow[] {
  const arts = ev?.articles || {}
  return Object.values(arts).filter((a) => a && (!monitoredOnly || a.monitor_stock))
}

/**
 * Assign each stock row to the first station (by sort_order) that lists it.
 * Unassigned rows go to "Zusätze". Empty groups are omitted.
 */
export function stockGroupsForItems(
  items: StockRow[] | null | undefined,
  stations: StationLike[] | null | undefined,
  { monitoredOnly = false }: { monitoredOnly?: boolean } = {},
): StockGroup[] {
  const rows = (items || []).filter((row) => row && (!monitoredOnly || row.monitor_stock))
  if (!rows.length) return []

  const orderedStations = sortedStations(stations ?? undefined)
  const byId = new Map(rows.map((row) => [Number(row.id), row]))
  const assigned = new Set<number>()
  const groups: StockGroup[] = []

  for (let i = 0; i < orderedStations.length; i += 1) {
    const st = orderedStations[i]
    const groupItems: StockRow[] = []
    for (const rawId of st.article_ids || []) {
      const id = Number(rawId)
      if (assigned.has(id)) continue
      const row = byId.get(id)
      if (!row) continue
      assigned.add(id)
      groupItems.push(row)
    }
    if (groupItems.length) {
      groupItems.sort(sortByName)
      groups.push({
        key: st.uuid || `station-${i}`,
        name: st.name || 'Station',
        items: groupItems,
      })
    }
  }

  const remainder = rows.filter((row) => !assigned.has(Number(row.id)))
  if (remainder.length) {
    remainder.sort(sortByName)
    groups.push({ key: ADDITIONS_KEY, name: ADDITIONS_NAME, items: remainder })
  }

  return groups
}

/** Event-scoped wrapper for Pi stock view (articles live on the event bundle). */
export function stockGroupsForEvent(
  ev: { articles?: Record<string, StockRow>; configuration?: { stations?: StationLike[] } } | null | undefined,
  { monitoredOnly = true }: { monitoredOnly?: boolean } = {},
): StockGroup[] {
  return stockGroupsForItems(
    articleListFromEvent(ev, monitoredOnly),
    ev?.configuration?.stations,
    { monitoredOnly },
  )
}
