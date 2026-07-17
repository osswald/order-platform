import { ref, computed, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { apiJson } from '@/api'
import { i18n } from '@/i18n'
import { resolveFormatLocale } from '@/utils/formatLocale'
import type { TaxCodeRead } from '@/types/api'

const cache = new Map<string, TaxCodeRead[]>()

function currentRatePercent(rates: TaxCodeRead['rates']): number | null {
  if (!Array.isArray(rates) || rates.length === 0) return null
  const today = new Date().toISOString().slice(0, 10)
  const active = rates
    .filter((rate) => {
      const from = rate.valid_from
      const to = rate.valid_to
      if (from && from > today) return false
      if (to && to < today) return false
      return true
    })
    .sort((a, b) => String(b.valid_from).localeCompare(String(a.valid_from)))
  const rate = active[0] ?? rates[rates.length - 1]
  return rate?.rate_percent ?? null
}

export function formatTaxCodeLabel(
  taxCode: TaxCodeRead,
  locale = 'de',
  countryCode?: string | null,
): string {
  const rate = currentRatePercent(taxCode.rates)
  if (rate == null) return taxCode.name
  const formatLocale = resolveFormatLocale(locale, countryCode)
  const formatted = i18n.global.n(rate, { key: 'percent', locale: formatLocale })
  return `${taxCode.name} (${formatted}%)`
}

export function useTaxCodes(countryIdRef: MaybeRefOrGetter<number | null | undefined>) {
  const taxCodes = ref<TaxCodeRead[]>([])
  const loading = ref(false)
  const loadError = ref('')

  const options = computed(() =>
    taxCodes.value.map((code) => ({
      value: code.id,
      label: formatTaxCodeLabel(code, i18n.global.locale.value, code.country?.code),
      title: formatTaxCodeLabel(code, i18n.global.locale.value, code.country?.code),
    })),
  )

  async function load() {
    const countryId = toValue(countryIdRef)
    if (countryId == null) {
      taxCodes.value = []
      return
    }
    const cacheKey = String(countryId)
    if (cache.has(cacheKey)) {
      taxCodes.value = cache.get(cacheKey) ?? []
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const data = await apiJson<TaxCodeRead[]>(`/tax-codes/?country_id=${countryId}`)
      cache.set(cacheKey, data)
      taxCodes.value = data
    } catch (e: unknown) {
      loadError.value = e instanceof Error ? e.message : 'Laden fehlgeschlagen'
      taxCodes.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => toValue(countryIdRef),
    () => {
      load()
    },
    { immediate: true },
  )

  return {
    taxCodes,
    options,
    loading,
    loadError,
    load,
  }
}

export function invalidateTaxCodesCache(countryId: number | null = null) {
  if (countryId == null) {
    cache.clear()
    return
  }
  cache.delete(String(countryId))
}
