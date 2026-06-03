<template>
  <div
    class="event-save-status-bar"
    :class="{
      'event-save-status-bar--dirty': aggregate.kind === 'dirty',
      'event-save-status-bar--saving': aggregate.kind === 'saving',
      'event-save-status-bar--error': aggregate.kind === 'error',
      'event-save-status-bar--saved': aggregate.kind === 'saved',
    }"
    role="status"
    aria-live="polite"
  >
    <v-progress-linear
      v-if="aggregate.kind === 'saving'"
      indeterminate
      color="primary"
      class="event-save-status-bar__progress"
    />
    <div class="event-save-status-bar__content">
      <v-icon v-if="icon" :icon="icon" size="small" class="event-save-status-bar__icon" />
      <span class="event-save-status-bar__text">{{ label }}</span>
      <span v-if="aggregate.kind === 'error' && aggregate.message" class="event-save-status-bar__detail">
        {{ aggregate.message }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  configurationStatus: { type: String, default: 'idle' },
  receiptStatus: { type: String, default: 'idle' },
  stockStatus: { type: String, default: 'idle' },
  stammdatenDirty: { type: Boolean, default: false },
  configurationError: { type: String, default: '' },
  receiptError: { type: String, default: '' },
  stockError: { type: String, default: '' },
})

const aggregate = computed(() => {
  const statuses = [
    props.configurationStatus,
    props.receiptStatus,
    props.stockStatus,
  ]
  if (props.stammdatenDirty) {
    return { kind: 'dirty' }
  }
  if (statuses.some((s) => s === 'saving')) {
    return { kind: 'saving' }
  }
  const errors = [props.configurationError, props.receiptError, props.stockError].filter(Boolean)
  if (statuses.some((s) => s === 'error') || errors.length) {
    return { kind: 'error', message: errors[0] || '' }
  }
  if (statuses.some((s) => s === 'dirty')) {
    return { kind: 'dirty' }
  }
  if (statuses.some((s) => s === 'saved')) {
    return { kind: 'saved' }
  }
  return { kind: 'idle' }
})

const label = computed(() => {
  switch (aggregate.value.kind) {
    case 'saving':
      return 'Wird gespeichert…'
    case 'error':
      return 'Speichern fehlgeschlagen'
    case 'dirty':
      return 'Ungespeicherte Änderungen'
    case 'saved':
      return 'Alle Änderungen gespeichert'
    default:
      return ''
  }
})

const icon = computed(() => {
  switch (aggregate.value.kind) {
    case 'saving':
      return 'mdi-cloud-sync'
    case 'error':
      return 'mdi-alert-circle-outline'
    case 'dirty':
      return 'mdi-circle-outline'
    case 'saved':
      return 'mdi-check-circle-outline'
    default:
      return null
  }
})
</script>

<style scoped>
.event-save-status-bar {
  margin-top: 1.5rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgba(var(--v-theme-on-surface), 0.03);
  position: sticky;
  bottom: 0;
  z-index: 2;
}

.event-save-status-bar--dirty {
  border-color: rgba(var(--v-theme-warning), 0.45);
  background: rgba(var(--v-theme-warning), 0.08);
}

.event-save-status-bar--saving {
  border-color: rgba(var(--v-theme-primary), 0.35);
}

.event-save-status-bar--error {
  border-color: rgba(var(--v-theme-error), 0.45);
  background: rgba(var(--v-theme-error), 0.08);
}

.event-save-status-bar--saved {
  border-color: rgba(var(--v-theme-success), 0.35);
  background: rgba(var(--v-theme-success), 0.06);
}

.event-save-status-bar__progress {
  margin: -0.75rem -1rem 0.5rem;
  border-radius: 8px 8px 0 0;
}

.event-save-status-bar__content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
}

.event-save-status-bar__detail {
  font-weight: 400;
  opacity: 0.85;
  font-size: 0.85rem;
}
</style>
