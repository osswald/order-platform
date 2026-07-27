<script setup lang="ts">
defineProps<{
  stationLabel: string
  eventName: string
  viewMode: 'orders' | 'products'
  loading: boolean
}>()

const emit = defineEmits<{
  setViewMode: [mode: 'orders' | 'products']
  refresh: []
}>()
</script>

<template>
  <header class="kitchen-header">
    <div class="kitchen-title">
      <strong>{{ stationLabel }}</strong>
      <span class="kitchen-event">{{ eventName }}</span>
    </div>

    <div class="kitchen-controls">
      <div class="view-toggle" role="tablist" aria-label="Ansicht">
        <button
          type="button"
          class="view-btn"
          :class="{ active: viewMode === 'orders' }"
          @click="emit('setViewMode', 'orders')"
        >
          Bestellungen
        </button>
        <button
          type="button"
          class="view-btn"
          :class="{ active: viewMode === 'products' }"
          @click="emit('setViewMode', 'products')"
        >
          Produkte
        </button>
      </div>
      <button type="button" class="btn small-btn" :disabled="loading" @click="emit('refresh')">
        Aktualisieren
      </button>
    </div>
  </header>
</template>

<style scoped>
.kitchen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
  flex-wrap: wrap;
}

.kitchen-title {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-width: 0;
}

.kitchen-title strong {
  font-size: 1.05rem;
  white-space: nowrap;
}

.kitchen-event {
  color: var(--muted);
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kitchen-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.small-btn {
  min-height: 40px;
  padding: 0.4rem 0.7rem;
  font-size: 0.92rem;
}

.view-toggle {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 999px;
  overflow: hidden;
}

.view-btn {
  border: none;
  background: var(--card);
  color: var(--text);
  padding: 0.45rem 0.75rem;
  font: inherit;
  font-size: 0.92rem;
  min-height: 40px;
}

.view-btn.active {
  background: var(--primary);
  color: white;
}
</style>
