<template>
  <div v-if="mobile" class="section-nav-accordion">
    <details
      v-for="section in sections"
      :key="section.id"
      class="section-nav-accordion-panel"
      :open="section.defaultOpen || undefined"
      @toggle="onPanelToggle(section.id, $event)"
    >
      <summary class="section-nav-accordion-header">
        <span class="section-nav-accordion-title">{{ section.title }}</span>
        <span class="section-nav-accordion-chevron" aria-hidden="true">
          <v-icon icon="mdi-chevron-down" size="small" />
        </span>
      </summary>
      <div v-if="isSectionMounted(section.id)" class="section-nav-accordion-content">
        <slot :name="section.id" />
      </div>
    </details>
  </div>

  <div v-else class="section-nav-split">
    <nav class="section-nav-nav" :aria-label="navAriaLabel">
      <button
        v-for="section in sections"
        :key="section.id"
        type="button"
        class="section-nav-item"
        :class="{ 'section-nav-item--active': activeTabModel === section.id }"
        :aria-current="activeTabModel === section.id ? 'page' : undefined"
        @click="activeTabModel = section.id"
      >
        {{ section.title }}
      </button>
    </nav>
    <div class="section-nav-main">
      <div class="section-nav-panel-body">
        <slot :name="activeTabModel" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SectionNavSection } from '@/types/ui'

const props = defineProps<{
  mobile?: boolean
  sections?: SectionNavSection[]
  activeTab?: string
  navAriaLabel: string
}>()

const emit = defineEmits<{
  'update:activeTab': [value: string]
}>()

const activeTabModel = computed({
  get() {
    const sections = props.sections ?? []
    if (props.activeTab && sections.some((s) => s.id === props.activeTab)) {
      return props.activeTab
    }
    return sections[0]?.id ?? ''
  },
  set(value: string) {
    emit('update:activeTab', value)
  },
})

const mountedSections = ref(new Set<string>())

function syncDefaultMountedSections(sections: SectionNavSection[]) {
  const next = new Set(mountedSections.value)
  for (const section of sections) {
    if (section.defaultOpen) next.add(section.id)
  }
  mountedSections.value = next
}

watch(
  () => props.sections,
  (sections) => syncDefaultMountedSections(sections ?? []),
  { immediate: true, deep: true },
)

function isSectionMounted(id: string): boolean {
  return mountedSections.value.has(id)
}

function onPanelToggle(id: string, event: ToggleEvent) {
  const target = event.target
  if (!(target instanceof HTMLDetailsElement) || !target.open) return
  const next = new Set(mountedSections.value)
  next.add(id)
  mountedSections.value = next
}
</script>

<style scoped>
.section-nav-accordion {
  display: flex;
  flex-direction: column;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.section-nav-accordion-panel {
  border: none;
  border-radius: 0;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: transparent;
  overflow: hidden;
}

.section-nav-accordion-panel:last-of-type {
  border-bottom: none;
}

.section-nav-accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1.1rem;
  cursor: pointer;
  list-style: none;
  user-select: none;
  background: rgba(var(--v-theme-on-surface), 0.02);
  transition: background-color 0.15s ease;
}

.section-nav-accordion-header:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.section-nav-accordion-header:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}

.section-nav-accordion-header::-webkit-details-marker {
  display: none;
}

.section-nav-accordion-title {
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.section-nav-accordion-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  opacity: 0.65;
  transition:
    transform 0.2s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.section-nav-accordion-panel[open] .section-nav-accordion-header {
  background: rgba(var(--v-theme-primary), 0.1);
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.section-nav-accordion-panel[open] .section-nav-accordion-chevron {
  color: rgb(var(--v-theme-primary));
  border-color: rgba(var(--v-theme-primary), 0.35);
}

.section-nav-accordion-panel[open] .section-nav-accordion-chevron :deep(.v-icon) {
  transform: rotate(180deg);
}

.section-nav-accordion-content {
  padding: 1.1rem 1.25rem 1.25rem;
  background: rgb(var(--v-theme-surface));
}

.section-nav-split {
  display: grid;
  grid-template-columns: minmax(10.5rem, 12.5rem) minmax(0, 1fr);
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  min-height: 12rem;
}

.section-nav-nav {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.5rem;
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgba(var(--v-theme-on-surface), 0.02);
  max-height: min(72vh, 36rem);
  overflow-y: auto;
  overscroll-behavior: contain;
}

.section-nav-item {
  display: block;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.section-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.section-nav-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}

.section-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.section-nav-main {
  min-width: 0;
  background: rgb(var(--v-theme-surface));
}

.section-nav-panel-body {
  padding: 1.1rem 1.25rem 1.25rem;
}

@media (max-width: 960px) {
  .section-nav-split {
    grid-template-columns: 1fr;
  }

  .section-nav-nav {
    flex-direction: row;
    flex-wrap: wrap;
    max-height: none;
    border-right: none;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    padding: 0.45rem 0.5rem;
  }

  .section-nav-item {
    width: auto;
    flex: 0 1 auto;
    white-space: nowrap;
    font-size: 0.75rem;
    padding: 0.35rem 0.55rem;
  }
}

@media (max-width: 992px) {
  .section-nav-accordion-content {
    padding: 0.85rem 0.9rem 1rem;
  }

  .section-nav-accordion-header {
    padding: 0.75rem 0.9rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .section-nav-accordion-header,
  .section-nav-accordion-chevron,
  .section-nav-accordion-chevron :deep(.v-icon),
  .section-nav-item {
    transition: none;
  }
}
</style>
