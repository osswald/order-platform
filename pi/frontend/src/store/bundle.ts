import { ref, computed } from 'vue'
import { api } from '@/api'
import type { EdgeBundleArticle, EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'
import { selectedEventId } from './sessions'

export const bundle = ref<EdgeBundleResponse | null>(null)
export const lastSyncAt = ref<string | null>(null)
export const syncError = ref('')
export const busy = ref(false)

let afterBundleLoaded: () => void = () => {}

export function setAfterBundleLoaded(fn: () => void): void {
  afterBundleLoaded = fn
}

export const selectedEvent = computed((): EdgeBundleEvent | null => {
  const b = bundle.value
  const id = selectedEventId.value
  if (!b?.events || id == null) return null
  return b.events.find((e) => Number(e.id) === Number(id)) || null
})

export function getArticle(articleId: number | string): EdgeBundleArticle | null {
  const ev = selectedEvent.value
  if (!ev?.articles) return null
  const key = String(articleId)
  return ev.articles[key] ?? ev.articles[Number(articleId) as unknown as string] ?? null
}

export function patchEventArticles(
  eventId: number,
  articlesMap: Record<string, Partial<EdgeBundleArticle>>,
): void {
  const b = bundle.value
  if (!b?.events || !articlesMap) return
  const eid = Number(eventId)
  for (const ev of b.events) {
    if (Number(ev.id) !== eid) continue
    const arts = { ...(ev.articles || {}) }
    for (const [key, patch] of Object.entries(articlesMap)) {
      const k = String(key)
      const existing = arts[k]
      if (existing) arts[k] = { ...existing, ...patch }
      else arts[k] = patch as EdgeBundleArticle
    }
    for (const base of Object.values(arts)) {
      if (!base?.additions) continue
      for (const add of base.additions) {
        const src = arts[String(add.article_id)]
        if (!src) continue
        if ('in_stock' in src) add.in_stock = src.in_stock
        if ('sellable' in src) add.sellable = src.sellable
        if ('monitor_stock' in src) add.monitor_stock = src.monitor_stock
      }
    }
    ev.articles = arts
    break
  }
}

export function bundleReady(): boolean {
  const b = bundle.value
  return Boolean(b && b.organisation_id != null)
}

export async function refreshBundle(): Promise<number> {
  const m = await api<{ last_sync_at?: string | null }>('/v1/meta')
  lastSyncAt.value = m.last_sync_at || null
  if (!lastSyncAt.value) {
    bundle.value = null
    return 0
  }
  try {
    const b = await api<EdgeBundleResponse>('/v1/bundle')
    bundle.value = b
    afterBundleLoaded()
    return (b.events || []).length
  } catch {
    bundle.value = null
    return 0
  }
}

export function articleName(articleId: number | string): string {
  const ev = selectedEvent.value
  const a = ev?.articles?.[String(articleId)]
  return a?.name || `Artikel #${articleId}`
}

export function stockArticlesForEvent(ev: EdgeBundleEvent | null | undefined): EdgeBundleArticle[] {
  if (!ev?.articles) return []
  return Object.values(ev.articles)
    .filter((a): a is EdgeBundleArticle => Boolean(a && a.monitor_stock))
    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'de'))
}
