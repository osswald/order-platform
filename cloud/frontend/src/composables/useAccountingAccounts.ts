import { ref, computed, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { apiJson } from '@/api'
import type { AccountingAccountRead } from '@/types/api'

const cache = new Map<string, AccountingAccountRead[]>()

function formatAccountLabel(account: AccountingAccountRead): string {
  return `${account.number} – ${account.name}`
}

export function useAccountingAccounts(organisationIdRef: MaybeRefOrGetter<number | null | undefined>) {
  const accounts = ref<AccountingAccountRead[]>([])
  const loading = ref(false)
  const loadError = ref('')

  const options = computed(() =>
    accounts.value.map((account) => ({
      value: account.id,
      label: formatAccountLabel(account),
      title: formatAccountLabel(account),
      is_default_for_article_categories: account.is_default_for_article_categories,
    })),
  )

  const categoryDefaultAccountId = computed(() => {
    const match = accounts.value.find((account) => account.is_default_for_article_categories)
    return match?.id ?? null
  })

  async function load() {
    const organisationId = toValue(organisationIdRef)
    if (organisationId == null) {
      accounts.value = []
      return
    }
    const cacheKey = String(organisationId)
    if (cache.has(cacheKey)) {
      accounts.value = cache.get(cacheKey) ?? []
      return
    }
    loading.value = true
    loadError.value = ''
    try {
      const data = await apiJson<AccountingAccountRead[]>(
        `/accounting-accounts/?organisation_id=${organisationId}`,
      )
      cache.set(cacheKey, data)
      accounts.value = data
    } catch (e: unknown) {
      loadError.value = e instanceof Error ? e.message : 'Laden fehlgeschlagen'
      accounts.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => toValue(organisationIdRef),
    () => {
      load()
    },
    { immediate: true },
  )

  return {
    accounts,
    options,
    loading,
    loadError,
    load,
    categoryDefaultAccountId,
  }
}

export function invalidateAccountingAccountsCache(organisationId: number | null = null) {
  if (organisationId == null) {
    cache.clear()
    return
  }
  cache.delete(String(organisationId))
}
