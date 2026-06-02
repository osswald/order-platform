<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="onBackdrop" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <template v-if="step === 'ask'">
        <header class="sheet-header">
          <h3>Zahlungsbeleg</h3>
          <p class="muted">Soll ein Zahlungsbeleg gedruckt werden?</p>
        </header>
        <div class="sheet-actions">
          <button type="button" class="btn" :disabled="busy" @click="emit('no')">Nein</button>
          <button type="button" class="btn primary" :disabled="busy" @click="emit('yes')">Drucken</button>
        </div>
      </template>
      <template v-else>
        <header class="sheet-header">
          <h3>Drucker wählen</h3>
          <p class="muted">Station oder Kasse für den Zahlungsbeleg</p>
        </header>
        <div class="target-list">
          <button
            v-for="t in targets"
            :key="t.uuid"
            type="button"
            class="btn target-btn"
            :disabled="busy"
            @click="emit('select-station', t.uuid)"
          >
            {{ t.label }}
          </button>
        </div>
        <div class="sheet-actions">
          <button type="button" class="btn" :disabled="busy" @click="emit('cancel')">Abbrechen</button>
        </div>
      </template>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  open: Boolean,
  step: { type: String, default: 'ask' },
  targets: { type: Array, default: () => [] },
  busy: Boolean,
})

const emit = defineEmits(['yes', 'no', 'cancel', 'select-station'])

function onBackdrop() {
  emit('cancel')
}
</script>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 155;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 156;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
  max-height: 70vh;
  overflow: auto;
}
.sheet-header h3 {
  margin: 0 0 0.25rem;
}
.target-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 1rem 0;
}
.target-btn {
  width: 100%;
  min-height: 48px;
  text-align: left;
  touch-action: manipulation;
}
.sheet-actions {
  display: flex;
  gap: 0.5rem;
}
.sheet-actions .btn {
  flex: 1;
  min-height: 48px;
  touch-action: manipulation;
}
</style>
