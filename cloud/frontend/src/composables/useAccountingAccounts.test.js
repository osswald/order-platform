import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { testI18n } from '../../tests/setup.js'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import {
  invalidateAccountingAccountsCache,
  useAccountingAccounts,
} from './useAccountingAccounts'

function mountAccountingAccounts(organisationIdRef) {
  let result
  const Comp = defineComponent({
    setup() {
      result = useAccountingAccounts(organisationIdRef)
      return () => null
    },
  })
  mount(Comp, { global: { plugins: [testI18n] } })
  return result
}

describe('useAccountingAccounts', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
    invalidateAccountingAccountsCache()
  })

  it('loads accounts for organisation', async () => {
    vi.mocked(apiJson).mockResolvedValue([
      { id: 5, number: '3400', name: 'Ertrag', is_default_for_article_categories: true },
      { id: 6, number: '1000', name: 'Kasse', is_default_for_article_categories: false },
    ])
    const orgId = ref(42)
    const { accounts, options, categoryDefaultAccountId } = mountAccountingAccounts(orgId)

    await flushPromises()
    expect(accounts.value).toHaveLength(2)
    expect(apiJson).toHaveBeenCalledWith('/accounting-accounts/?organisation_id=42')
    expect(options.value[0].label).toBe('3400 – Ertrag')
    expect(categoryDefaultAccountId.value).toBe(5)
  })

  it('clears accounts when organisation id is null', async () => {
    const orgId = ref(null)
    const { accounts } = mountAccountingAccounts(orgId)

    await flushPromises()
    expect(accounts.value).toEqual([])
    expect(apiJson).not.toHaveBeenCalled()
  })

  it('uses org-scoped cache', async () => {
    vi.mocked(apiJson).mockResolvedValue([
      { id: 5, number: '3400', name: 'Ertrag', is_default_for_article_categories: false },
    ])
    const orgId = ref(7)
    mountAccountingAccounts(orgId)
    await flushPromises()
    expect(apiJson).toHaveBeenCalledTimes(1)

    mountAccountingAccounts(ref(7))
    await nextTick()
    expect(apiJson).toHaveBeenCalledTimes(1)
  })

  it('sets loadError on failure', async () => {
    vi.mocked(apiJson).mockRejectedValue(new Error('forbidden'))
    const { loadError, accounts } = mountAccountingAccounts(ref(1))

    await flushPromises()
    expect(loadError.value).toBe('forbidden')
    expect(accounts.value).toEqual([])
  })
})
