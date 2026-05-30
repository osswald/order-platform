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
          <v-icon icon="mdi-chevron-down" size="small" />
        </span>
      </summary>
      <div class="event-config-accordion-content">
        <slot :name="section.id" />
      </div>
    </details>
  </div>

  <div v-else class="event-config-tabs">
    <v-tabs
      v-model="activeTabModel"
      show-arrows
      density="comfortable"
      class="event-config-tablist"
    >
      <v-tab
        v-for="section in sections"
        :key="section.id"
        :value="section.id"
        class="event-config-tab"
      >
        {{ section.title }}
      </v-tab>
    </v-tabs>
    <v-window v-model="activeTabModel" class="event-config-tabpanels">
      <v-window-item
        v-for="section in sections"
        :key="section.id"
        :value="section.id"
        class="event-config-tabpanel"
      >
        <div class="event-config-tabpanel-body">
          <slot :name="section.id" />
        </div>
      </v-window-item>
    </v-window>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.event-config-accordion-panel {
  border: none;
  border-radius: 0;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
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
  cursor: pointer;
  list-style: none;
  user-select: none;
  background: rgba(var(--v-theme-on-surface), 0.02);
  transition: background-color 0.15s ease;
}

.event-config-accordion-header:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.event-config-accordion-header:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
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
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  opacity: 0.65;
  transition:
    transform 0.2s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.event-config-accordion-panel[open] .event-config-accordion-header {
  background: rgba(var(--v-theme-primary), 0.1);
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.event-config-accordion-panel[open] .event-config-accordion-chevron {
  color: rgb(var(--v-theme-primary));
  border-color: rgba(var(--v-theme-primary), 0.35);
}

.event-config-accordion-panel[open] .event-config-accordion-chevron :deep(.v-icon) {
  transform: rotate(180deg);
}

.event-config-accordion-content {
  padding: 1.1rem 1.25rem 1.25rem;
  background: rgb(var(--v-theme-surface));
}

.event-config-tabs {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.event-config-tablist {
  background: rgba(var(--v-theme-on-surface), 0.02);
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.event-config-tabpanels {
  background: rgb(var(--v-theme-surface));
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
  .event-config-accordion-chevron :deep(.v-icon) {
    transition: none;
  }
}
</style>
