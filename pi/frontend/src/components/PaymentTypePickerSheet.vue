<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="onCancel" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true" aria-labelledby="pay-type-title">
      <header class="sheet-header">
        <h3 id="pay-type-title">Zahlungsart</h3>
        <p v-if="amountLabel" class="muted">Betrag: {{ amountLabel }}</p>
      </header>
      <div class="type-buttons">
        <button
          v-for="t in types"
          :key="t"
          type="button"
          class="btn type-btn primary"
          @click="$emit('select', t)"
        >
          {{ label(t) }}
        </button>
      </div>
      <div class="sheet-actions">
        <button type="button" class="btn" @click="onCancel">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { paymentTypeLabel } from '../utils/paymentTypes'

defineProps({
  open: Boolean,
  types: { type: Array, default: () => [] },
  amountLabel: { type: String, default: '' },
})

const emit = defineEmits(['select', 'cancel'])

function label(t) {
  return paymentTypeLabel(t)
}

function onCancel() {
  emit('cancel')
}
</script>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 150;
}
.sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 151;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  padding: 1rem 1rem calc(1rem + env(safe-area-inset-bottom));
}
.sheet-header h3 {
  margin: 0 0 0.25rem;
}
.type-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 1rem 0;
}
.type-btn {
  width: 100%;
  min-height: 52px;
  font-size: 1.1rem;
  font-weight: 700;
}
.sheet-actions .btn {
  width: 100%;
  min-height: 44px;
}
</style>
