import { computed, ref, unref, watch } from 'vue'
import type { MaybeRefOrGetter, WatchSource } from 'vue'

export const DEFAULT_CLIENT_PAGE_SIZE = 20

export interface ClientPaginationOptions {
  pageSize?: number
  resetOn?: WatchSource<unknown> | unknown[]
}

export function useClientPagination<T>(
  filteredItems: MaybeRefOrGetter<T[] | null | undefined>,
  options: ClientPaginationOptions = {},
) {
  const pageSize = options.pageSize ?? DEFAULT_CLIENT_PAGE_SIZE
  const currentPage = ref(1)
  const resetOn = options.resetOn ?? []

  watch(
    resetOn as WatchSource<unknown>,
    () => {
      currentPage.value = 1
    },
    { deep: true },
  )

  const totalPages = computed(() =>
    Math.max(1, Math.ceil((unref(filteredItems)?.length ?? 0) / pageSize)),
  )

  watch(totalPages, (pages) => {
    if (currentPage.value > pages) currentPage.value = pages
  })

  return { currentPage, pageSize, totalPages }
}
