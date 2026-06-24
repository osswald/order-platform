import { ref, computed, toValue, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ComposerTranslation } from 'vue-i18n'
import { apiJson } from '@/api'
import type { PaymentTypeRead } from '@/types/api'

const cache = new Map<string, PaymentTypeRead[]>()

export function paymentTypeLabel(slug: string, t: ComposerTranslation): string {
  const key = `paymentTypes.${slug}`
  const translated = t(key)
  return translated === key ? slug : translated
}

export interface UsePaymentTypesOptions {
  activeOnly?: boolean
}

export function usePaymentTypes(options: UsePaymentTypesOptions = {}) {
  const { activeOnly = true } = options
  const { t } = useI18n()
  const paymentTypes = ref<PaymentTypeRead[]>([])
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
      paymentTypes.value = cache.get(cacheKey) ?? []
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const query = activeOnly ? '?active_only=true' : ''
      const data = await apiJson<PaymentTypeRead[]>(`/payment-types/${query}`)
      cache.set(cacheKey, data)
      paymentTypes.value = data
    } catch (e: unknown) {
      loadError.value = e instanceof Error ? e.message : 'Laden fehlgeschlagen'
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
    paymentTypeLabel: (slug: string) => paymentTypeLabel(slug, t),
  }
}

export function invalidatePaymentTypesCache() {
  cache.clear()
}
