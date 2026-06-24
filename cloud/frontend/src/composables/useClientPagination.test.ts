import { describe, expect, it } from 'vitest'
import { computed, defineComponent, nextTick, ref } from 'vue'
import type { Ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { useClientPagination, DEFAULT_CLIENT_PAGE_SIZE } from './useClientPagination'

function mountPagination(itemsRef: Ref<unknown[]>, options: Record<string, unknown> = {}) {
  let pagination!: ReturnType<typeof useClientPagination>
  const wrapper = mount(
    defineComponent({
      setup() {
        pagination = useClientPagination(itemsRef, options)
        return pagination
      },
      template: '<div />',
    }),
  )
  return { wrapper, pagination }
}

describe('useClientPagination', () => {
  it('uses default page size and starts on page 1', () => {
    const items = ref([])
    const { pagination } = mountPagination(items)
    expect(pagination.currentPage.value).toBe(1)
    expect(pagination.pageSize).toBe(DEFAULT_CLIENT_PAGE_SIZE)
  })

  it('computes totalPages from filtered item count', async () => {
    const items = ref(Array.from({ length: 11 }, (_, i) => ({ id: i + 1 })))
    const { pagination } = mountPagination(items)
    expect(pagination.totalPages.value).toBe(1)

    items.value = Array.from({ length: 21 }, (_, i) => ({ id: i + 1 }))
    await nextTick()
    expect(pagination.totalPages.value).toBe(2)

    items.value = []
    await nextTick()
    expect(pagination.totalPages.value).toBe(1)
  })

  it('supports custom pageSize', async () => {
    const items = ref(Array.from({ length: 25 }, (_, i) => ({ id: i + 1 })))
    const { pagination } = mountPagination(items, { pageSize: 10 })
    expect(pagination.pageSize).toBe(10)
    expect(pagination.totalPages.value).toBe(3)
  })

  it('resets currentPage when resetOn sources change', async () => {
    const items = ref([{ id: 1 }])
    const searchQuery = ref('')
    const { pagination } = mountPagination(items, { resetOn: [searchQuery] })

    pagination.currentPage.value = 3
    searchQuery.value = 'test'
    await nextTick()
    expect(pagination.currentPage.value).toBe(1)
  })

  it('clamps currentPage when totalPages shrinks', async () => {
    const items = ref(Array.from({ length: 41 }, (_, i) => ({ id: i + 1 })))
    const { pagination } = mountPagination(items)

    pagination.currentPage.value = 3
    items.value = [{ id: 1 }]
    await flushPromises()
    expect(pagination.currentPage.value).toBe(1)
  })

  it('accepts computed filtered items', async () => {
    const allItems = ref(Array.from({ length: 25 }, (_, i) => ({ id: i + 1, active: true })))
    const filteredItems = computed(() => allItems.value.filter((item) => item.active))
    const { pagination } = mountPagination(filteredItems, { pageSize: 10 })

    expect(pagination.totalPages.value).toBe(3)

    allItems.value = allItems.value.map((item, index) => ({ ...item, active: index < 5 }))
    await nextTick()
    expect(pagination.totalPages.value).toBe(1)
  })
})
