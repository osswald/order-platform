import { ref, computed, toValue, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../api'

const cache = new Map()

export function paymentTypeLabel(slug, t) {
  const key = `paymentTypes.${slug}`
  const translated = t(key)
  return translated === key ? slug : translated
}

export function usePaymentTypes(options = {}) {
  const { activeOnly = true } = options
  const { t } = useI18n()
  const paymentTypes = ref([])
  const loading = ref(false)
  const loadError = ref('')

  const optionsList = computed(() =>
    paymentTypes.value.map((row) => ({
      value: row.slug,
      id: row.id,
      label: paymentTypeLabel(row.slug, t),
      title: paymentTypeLabel(row.slug, t),
      sort_order: row.sort_order,
      is_active: row.is_active,
    })),
  )

  async function load() {
    const cacheKey = activeOnly ? 'active' : 'all'
    if (cache.has(cacheKey)) {
      paymentTypes.value = cache.get(cacheKey)
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const query = activeOnly ? '?active_only=true' : ''
      const res = await apiFetch(`/payment-types/${query}`)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      cache.set(cacheKey, data)
      paymentTypes.value = data
    } catch (e) {
      loadError.value = e.message || 'Laden fehlgeschlagen'
      paymentTypes.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => toValue(activeOnly),
    () => {
      load()
    },
    { immediate: true },
  )

  return {
    paymentTypes,
    options: optionsList,
    loading,
    loadError,
    load,
    paymentTypeLabel: (slug) => paymentTypeLabel(slug, t),
  }
}

export function invalidatePaymentTypesCache() {
  cache.clear()
}
