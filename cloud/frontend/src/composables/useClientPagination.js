import { computed, ref, unref, watch } from 'vue'

export const DEFAULT_CLIENT_PAGE_SIZE = 20

export function useClientPagination(filteredItems, options = {}) {
  const pageSize = options.pageSize ?? DEFAULT_CLIENT_PAGE_SIZE
  const currentPage = ref(1)
  const resetOn = options.resetOn ?? []

  watch(resetOn, () => {
    currentPage.value = 1
  })

  const totalPages = computed(() =>
    Math.max(1, Math.ceil((unref(filteredItems)?.length ?? 0) / pageSize)),
  )

  watch(totalPages, (pages) => {
    if (currentPage.value > pages) currentPage.value = pages
  })

  return { currentPage, pageSize, totalPages }
}
