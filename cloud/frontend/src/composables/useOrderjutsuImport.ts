import { computed, ref } from 'vue'
import { apiJson } from '@/api'
import type { components } from '@/types/api.generated'

export type OrderjutsuImportPreview = components['schemas']['OrderjutsuImportPreview']
export type OrderjutsuImportCommit = components['schemas']['OrderjutsuImportCommit']
export type OrderjutsuImportCommitResult = components['schemas']['OrderjutsuImportCommitResult']

export type WizardStepId =
  | 'upload'
  | 'event'
  | 'waiters'
  | 'articles'
  | 'categories'
  | 'additions'
  | 'ingredients'
  | 'stations'
  | 'stock'
  | 'layouts'
  | 'vouchers'
  | 'review'

export type ArticleAction = 'link_existing' | 'create_new' | 'skip'
export type WaiterAction = 'link_existing' | 'create_org_waiter' | 'event_only' | 'skip'
export type IngredientAction = 'link_existing' | 'create_new'

function toDatetimeLocalValue(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const jsonRequestInit = {
  headers: { 'Content-Type': 'application/json' },
} as const

export function useOrderjutsuImport(organisationId: () => number | null) {
  const rawPayload = ref<Record<string, unknown> | null>(null)
  const preview = ref<OrderjutsuImportPreview | null>(null)
  const previewLoading = ref(false)
  const previewError = ref('')
  const commitLoading = ref(false)
  const commitError = ref('')

  const eventName = ref('')
  const eventStart = ref('')
  const eventEnd = ref('')
  const enableIngredients = ref(false)
  const defaultCategoryId = ref<number | null>(null)
  const importStock = ref(true)
  const importVouchers = ref(true)

  const articleActions = ref<Record<number, { action: ArticleAction; articleId: number | null }>>({})
  const waiterActions = ref<Record<number, { action: WaiterAction; waiterId: number | null }>>({})
  const ingredientActions = ref<Record<number, { action: IngredientAction; ingredientId: number | null }>>({})
  const stationPrinters = ref<Record<number, number | null>>({})

  const visibleSteps = computed((): WizardStepId[] => {
    const steps: WizardStepId[] = ['upload']
    if (!preview.value) return steps
    steps.push('event', 'waiters', 'articles', 'categories')
    if ((preview.value.product_extras || []).length) steps.push('additions')
    if (preview.value.has_ingredients) steps.push('ingredients')
    steps.push('stations', 'stock', 'layouts')
    if (preview.value.has_vouchers) steps.push('vouchers')
    steps.push('review')
    return steps
  })

  function initFromPreview(data: OrderjutsuImportPreview) {
    preview.value = data
    eventName.value = data.event.name
    eventStart.value = toDatetimeLocalValue(data.event.start)
    eventEnd.value = toDatetimeLocalValue(data.event.end)
    enableIngredients.value = data.will_enable_ingredients
    importVouchers.value = data.has_vouchers

    const articles: Record<number, { action: ArticleAction; articleId: number | null }> = {}
    for (const p of data.products || []) {
      if (p.ingredient_only) continue
      let action: ArticleAction = 'create_new'
      let articleId: number | null = null
      if (p.match_kind === 'import_number' || p.match_kind === 'exact') {
        action = 'link_existing'
        articleId = p.matched_article_id ?? null
      } else if (p.match_kind === 'ambiguous') {
        action = 'create_new'
      }
      articles[p.ref] = { action, articleId }
    }
    articleActions.value = articles

    const waiters: Record<number, { action: WaiterAction; waiterId: number | null }> = {}
    for (const c of data.cashiers || []) {
      waiters[c.index] = {
        action: c.matched_waiter_id ? 'link_existing' : 'event_only',
        waiterId: c.matched_waiter_id ?? null,
      }
    }
    waiterActions.value = waiters

    const ingredients: Record<number, { action: IngredientAction; ingredientId: number | null }> = {}
    for (const ing of data.ingredient_matches || []) {
      ingredients[ing.ref] = {
        action: ing.matched_ingredient_id ? 'link_existing' : 'create_new',
        ingredientId: ing.matched_ingredient_id ?? null,
      }
    }
    ingredientActions.value = ingredients

    const stations: Record<number, number | null> = {}
    for (const st of data.stations || []) {
      stations[st.index] = null
    }
    stationPrinters.value = stations
  }

  async function loadPreview(file: File) {
    previewError.value = ''
    previewLoading.value = true
    try {
      const text = await file.text()
      const payload = JSON.parse(text) as Record<string, unknown>
      rawPayload.value = payload
      const orgId = organisationId()
      if (!orgId) throw new Error('No organisation selected')
      const data = await apiJson<OrderjutsuImportPreview>('/events/import/orderjutsu/preview', {
        method: 'POST',
        ...jsonRequestInit,
        body: JSON.stringify({ organisation_id: orgId, payload }),
      })
      initFromPreview(data)
      return data
    } catch (e: unknown) {
      previewError.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      previewLoading.value = false
    }
  }

  function buildCommitBody(): OrderjutsuImportCommit {
    const orgId = organisationId()
    const payload = rawPayload.value
    const data = preview.value
    if (!orgId || !payload || !data) throw new Error('Import not ready')

    return {
      organisation_id: orgId,
      payload,
      event: {
        name: eventName.value.trim(),
        start: new Date(eventStart.value).toISOString(),
        end: new Date(eventEnd.value).toISOString(),
        cash_registers_enabled: data.has_cash_registers,
        vouchers_enabled: importVouchers.value && data.has_vouchers,
      },
      articles: Object.entries(articleActions.value).map(([ref, row]) => ({
        ref: Number(ref),
        action: row.action,
        article_id: row.action === 'link_existing' ? row.articleId : null,
      })),
      ingredients: Object.entries(ingredientActions.value).map(([ref, row]) => ({
        ref: Number(ref),
        action: row.action,
        ingredient_id: row.action === 'link_existing' ? row.ingredientId : null,
      })),
      cashiers: Object.entries(waiterActions.value).map(([index, row]) => ({
        index: Number(index),
        action: row.action,
        waiter_id: row.action === 'link_existing' ? row.waiterId : null,
      })),
      default_article_category_id: defaultCategoryId.value ?? 0,
      enable_ingredients: enableIngredients.value,
      stations: Object.entries(stationPrinters.value).map(([index, printerId]) => ({
        index: Number(index),
        printer_appliance_id: printerId,
      })),
      import_stock: importStock.value,
      import_vouchers: importVouchers.value,
    }
  }

  async function commitImport(): Promise<OrderjutsuImportCommitResult> {
    commitError.value = ''
    commitLoading.value = true
    try {
      const body = buildCommitBody()
      return await apiJson<OrderjutsuImportCommitResult>('/events/import/orderjutsu/commit', {
        method: 'POST',
        ...jsonRequestInit,
        body: JSON.stringify(body),
      })
    } catch (e: unknown) {
      commitError.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      commitLoading.value = false
    }
  }

  function setAllUnmatchedArticles(action: ArticleAction) {
    if (!preview.value) return
    for (const p of preview.value.products) {
      if (p.ingredient_only) continue
      if (p.match_kind === 'none' || p.match_kind === 'ambiguous') {
        articleActions.value[p.ref] = { action, articleId: null }
      }
    }
  }

  function setAllUnmatchedWaiters(action: WaiterAction) {
    if (!preview.value) return
    for (const c of preview.value.cashiers) {
      if (!c.matched_waiter_id) {
        waiterActions.value[c.index] = { action, waiterId: null }
      }
    }
  }

  return {
    rawPayload,
    preview,
    previewLoading,
    previewError,
    commitLoading,
    commitError,
    eventName,
    eventStart,
    eventEnd,
    enableIngredients,
    defaultCategoryId,
    importStock,
    importVouchers,
    articleActions,
    waiterActions,
    ingredientActions,
    stationPrinters,
    visibleSteps,
    loadPreview,
    buildCommitBody,
    commitImport,
    setAllUnmatchedArticles,
    setAllUnmatchedWaiters,
  }
}
