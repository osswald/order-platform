<template>
  <Teleport to="body">
    <div v-if="open" class="receipt-sheet-backdrop" @click.self="emit('close')" />
    <div v-if="open" class="receipt-sheet" role="dialog" aria-modal="true" aria-labelledby="receipt-sheet-title">
      <header class="receipt-sheet-header">
        <h3 id="receipt-sheet-title">Emulierte Belege</h3>
        <button type="button" class="btn receipt-sheet-close" aria-label="Schliessen" @click="emit('close')">
          Schliessen
        </button>
      </header>
      <div class="receipt-sheet-body">
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  open: Boolean,
})

const emit = defineEmits(['close'])
</script>

<style scoped>
.receipt-sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 150;
}

.receipt-sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 151;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}

.receipt-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1rem 0.5rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.receipt-sheet-header h3 {
  margin: 0;
  font-size: 1rem;
}

.receipt-sheet-close {
  min-height: 36px;
  padding: 0.35rem 0.75rem;
  font-size: 0.875rem;
}

.receipt-sheet-body {
  overflow-y: auto;
  padding: 0 0 calc(1rem + var(--safe-bottom));
  flex: 1;
  min-height: 0;
}
</style>
