<template>
  <div v-if="mobile" class="event-config-accordion">
    <details
      v-for="section in sections"
      :key="section.id"
      class="event-config-accordion-panel"
      :open="section.defaultOpen || undefined"
    >
      <summary class="event-config-accordion-header">
        <span class="event-config-accordion-title">{{ section.title }}</span>
        <span class="event-config-accordion-chevron" aria-hidden="true">
          <i class="pi pi-chevron-down" />
        </span>
      </summary>
      <div class="event-config-accordion-content">
        <slot :name="section.id" />
      </div>
    </details>
  </div>

  <Tabs
    v-else
    v-model:value="activeTabModel"
    scrollable
    class="event-config-tabs"
  >
    <TabList class="event-config-tablist">
      <Tab
        v-for="section in sections"
        :key="section.id"
        :value="section.id"
        class="event-config-tab"
      >
        {{ section.title }}
      </Tab>
    </TabList>
    <TabPanels class="event-config-tabpanels">
      <TabPanel
        v-for="section in sections"
        :key="section.id"
        :value="section.id"
        class="event-config-tabpanel"
      >
        <div class="event-config-tabpanel-body">
          <slot :name="section.id" />
        </div>
      </TabPanel>
    </TabPanels>
  </Tabs>
</template>

<script setup>
import { computed } from 'vue'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'

const props = defineProps({
  mobile: {
    type: Boolean,
    default: false,
  },
  sections: {
    type: Array,
    default: () => [],
  },
  activeTab: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:activeTab'])

const activeTabModel = computed({
  get() {
    if (props.activeTab && props.sections.some((s) => s.id === props.activeTab)) {
      return props.activeTab
    }
    return props.sections[0]?.id ?? ''
  },
  set(value) {
    emit('update:activeTab', value)
  },
})
</script>

<style scoped>
.event-config-accordion {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-ground);
  overflow: hidden;
  box-shadow: var(--p-card-shadow, 0 1px 2px rgba(0, 0, 0, 0.06));
}

.event-config-accordion-panel {
  border: none;
  border-radius: 0;
  border-bottom: 1px solid var(--p-content-border-color);
  background: transparent;
  overflow: hidden;
}

.event-config-accordion-panel:last-of-type {
  border-bottom: none;
}

.event-config-accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1.1rem;
  color: var(--p-text-color);
  cursor: pointer;
  list-style: none;
  user-select: none;
  background: var(--p-surface-section, var(--p-surface-card));
  transition: background-color 0.15s ease;
}

.event-config-accordion-header:hover {
  background: var(
    --p-content-hover-background,
    color-mix(in srgb, var(--p-primary-color) 8%, var(--p-surface-section))
  );
}

.event-config-accordion-header:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: -2px;
}

.event-config-accordion-header::-webkit-details-marker {
  display: none;
}

.event-config-accordion-title {
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.event-config-accordion-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  border-radius: var(--p-border-radius-md);
  background: var(--p-surface-ground);
  border: 1px solid var(--p-content-border-color);
  color: var(--p-text-muted-color);
  transition:
    transform 0.2s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.event-config-accordion-chevron i {
  font-size: 0.75rem;
  transition: transform 0.2s ease;
}

.event-config-accordion-panel[open] .event-config-accordion-header {
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-section, var(--p-surface-card)));
  border-bottom: 1px solid var(--p-content-border-color);
}

.event-config-accordion-panel[open] .event-config-accordion-chevron {
  color: var(--p-primary-color);
  border-color: color-mix(in srgb, var(--p-primary-color) 35%, var(--p-content-border-color));
  background: var(--p-surface-section, var(--p-surface-card));
}

.event-config-accordion-panel[open] .event-config-accordion-chevron i {
  transform: rotate(180deg);
}

.event-config-accordion-content {
  padding: 1.1rem 1.25rem 1.25rem;
  background: var(--p-surface-card);
}

.event-config-tabs {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-surface-card);
  overflow: hidden;
  box-shadow: var(--p-card-shadow, 0 1px 2px rgba(0, 0, 0, 0.06));
}

.event-config-tabs :deep(.p-tablist) {
  background: var(--p-surface-ground);
  border-bottom: 1px solid var(--p-content-border-color);
}

.event-config-tabs :deep(.p-tablist-tab-list) {
  gap: 0.15rem;
  padding: 0.35rem 0.5rem 0;
}

.event-config-tabs :deep(.p-tab) {
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: var(--p-border-radius-md) var(--p-border-radius-md) 0 0;
  margin: 0;
  padding: 0.65rem 0.9rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: transparent;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.event-config-tabs :deep(.p-tab:hover) {
  color: var(--p-text-color);
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
}

.event-config-tabs :deep(.p-tab[data-p-active='true']),
.event-config-tabs :deep(.p-tab.p-tab-active) {
  color: var(--p-primary-color);
  background: var(--p-surface-card);
  border-color: var(--p-content-border-color);
}

.event-config-tabs :deep(.p-tabpanels) {
  background: var(--p-surface-card);
  padding: 0;
}

.event-config-tabpanel-body {
  padding: 1.1rem 1.25rem 1.25rem;
}

@media (max-width: 768px) {
  .event-config-accordion-content {
    padding: 0.85rem 0.9rem 1rem;
  }

  .event-config-accordion-header {
    padding: 0.75rem 0.9rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .event-config-accordion-header,
  .event-config-accordion-chevron,
  .event-config-accordion-chevron i,
  .event-config-tabs :deep(.p-tab) {
    transition: none;
  }
}
</style>
