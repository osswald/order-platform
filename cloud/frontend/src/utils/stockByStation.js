const ADDITIONS_KEY = 'additions'
const ADDITIONS_NAME = 'Zusätze'

function sortByName(a, b) {
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'de')
}

/**
 * Assign each stock row to the first station (by config order) that lists it.
 * Unassigned rows go to "Zusätze". Empty groups are omitted.
 */
export function stockGroupsForItems(items, stations, { monitoredOnly = false } = {}) {
  const rows = (items || []).filter((row) => row && (!monitoredOnly || row.monitor_stock))
  if (!rows.length) return []

  const orderedStations = (stations || []).slice()
  const byId = new Map(rows.map((row) => [Number(row.id), row]))
  const assigned = new Set()
  const groups = []

  for (let i = 0; i < orderedStations.length; i += 1) {
    const st = orderedStations[i]
    const groupItems = []
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
