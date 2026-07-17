import { toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Bidirectional sync between a section/tab id and `?section=` in the URL.
 * Uses replace so tab switches do not stack history entries.
 */
export function useSectionQuerySync(
  activeTab: Ref<string>,
  sections: MaybeRefOrGetter<{ id: string }[]>,
  options: { enabled?: MaybeRefOrGetter<boolean> } = {},
) {
  const route = useRoute()
  const router = useRouter()
  const enabled = options.enabled ?? true

  function isEnabled(): boolean {
    return toValue(enabled)
  }

  function sectionIds(): string[] {
    return toValue(sections).map((section) => section.id)
  }

  function applySectionFromQuery() {
    if (!isEnabled()) return
    const section = typeof route.query.section === 'string' ? route.query.section : ''
    if (!section) return
    if (sectionIds().includes(section)) {
      activeTab.value = section
    }
  }

  function writeSectionToQuery() {
    if (!isEnabled()) return
    const tab = activeTab.value
    if (!sectionIds().includes(tab)) return
    if (route.query.section === tab) return
    void router.replace({ query: { ...route.query, section: tab } })
  }

  watch(
    () => [route.query.section, toValue(sections), isEnabled()] as const,
    applySectionFromQuery,
    { immediate: true },
  )

  watch(
    () => [activeTab.value, toValue(sections), isEnabled()] as const,
    writeSectionToQuery,
    { immediate: true },
  )
}
