const ADDITIONS_KEY = 'additions'
const ADDITIONS_NAME = 'Zusätze'

function sortByName(a, b) {
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'de')
}

function sortedStations(stations) {
  return (stations || [])
    .slice()
    .sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0))
}

function articleList(ev, monitoredOnly) {
  const arts = ev?.articles || {}
  return Object.values(arts).filter((a) => a && (!monitoredOnly || a.monitor_stock))
}

/**
 * Assign each article to the first station (by sort_order) that lists it.
 * Unassigned articles go to "Zusätze". Empty groups are omitted.
 */
export function stockGroupsForEvent(ev, { monitoredOnly = true } = {}) {
  const articles = articleList(ev, monitoredOnly)
  if (!articles.length) return []

  const stations = sortedStations(ev?.configuration?.stations)
  const byId = new Map(articles.map((a) => [Number(a.id), a]))
  const assigned = new Set()
  const groups = []

  for (const st of stations) {
    const items = []
    for (const rawId of st.article_ids || []) {
      const id = Number(rawId)
      if (assigned.has(id)) continue
      const art = byId.get(id)
      if (!art) continue
      assigned.add(id)
      items.push(art)
    }
    if (items.length) {
      items.sort(sortByName)
      groups.push({
        key: st.uuid || String(st.name || groups.length),
        name: st.name || 'Station',
        items,
      })
    }
  }

  const remainder = articles.filter((a) => !assigned.has(Number(a.id)))
  if (remainder.length) {
    remainder.sort(sortByName)
    groups.push({ key: ADDITIONS_KEY, name: ADDITIONS_NAME, items: remainder })
  }

  return groups
}
