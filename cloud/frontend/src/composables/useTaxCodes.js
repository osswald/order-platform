import { ref, computed, unref, watch } from 'vue'
import { apiFetch } from '../api'

const cache = new Map()

function currentRatePercent(rates) {
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

export function formatTaxCodeLabel(taxCode, locale = 'de') {
  const rate = currentRatePercent(taxCode.rates)
  if (rate == null) return taxCode.name
  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(rate)
  return `${taxCode.name} (${formatted}%)`
}

export function useTaxCodes(countryIdRef) {
  const taxCodes = ref([])
  const loading = ref(false)
  const loadError = ref('')

  const options = computed(() =>
    taxCodes.value.map((code) => ({
      value: code.id,
      label: formatTaxCodeLabel(code),
      title: formatTaxCodeLabel(code),
    })),
  )

  async function load() {
    const countryId = unref(countryIdRef)
    if (countryId == null) {
      taxCodes.value = []
      return
    }
    const cacheKey = String(countryId)
    if (cache.has(cacheKey)) {
      taxCodes.value = cache.get(cacheKey)
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const res = await apiFetch(`/tax-codes/?country_id=${countryId}`)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      cache.set(cacheKey, data)
      taxCodes.value = data
    } catch (e) {
      loadError.value = e.message || 'Laden fehlgeschlagen'
      taxCodes.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => unref(countryIdRef),
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

export function invalidateTaxCodesCache(countryId = null) {
  if (countryId == null) {
    cache.clear()
    return
  }
  cache.delete(String(countryId))
}
