<template>
  <div
    v-if="shiftCloseDialogOpen"
    class="shift-overlay"
    role="dialog"
    aria-modal="true"
    :style="overlayStyle"
  >
    <div class="shift-card">
      <h2>Schicht beenden</h2>
      <p class="muted">Kassenbestand zählen (CHF)</p>
      <p v-if="shiftCloseExpectedLabel" class="muted expected">
        Erwartet ca. {{ shiftCloseExpectedLabel }}
      </p>
      <label class="field-label">
        Betrag (CHF)
        <input
          v-model="shiftCloseAmountChf"
          type="text"
          inputmode="decimal"
          class="input amount-input"
        />
      </label>
      <p v-if="shiftCloseError" class="err">{{ shiftCloseError }}</p>
      <div class="actions">
        <button type="button" class="btn" @click="cancelShiftClose">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirmShiftClose">Beenden</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useKeyboardBottomInset } from '@/composables/useKeyboardBottomInset'
import {
  cancelShiftClose,
  confirmShiftClose,
  shiftCloseAmountChf,
  shiftCloseDialogOpen,
  shiftCloseError,
  shiftCloseExpectedLabel,
} from '@/composables/useShiftSession'

const keyboardBottomInset = useKeyboardBottomInset()
const overlayStyle = computed(() => ({
  paddingBottom: `calc(1rem + ${keyboardBottomInset.value}px)`,
}))
</script>

<style scoped>
.shift-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}
.shift-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  width: 100%;
  max-width: 22rem;
  color: var(--text);
}
.shift-card h2 {
  margin: 0 0 0.35rem;
}
.expected {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
}
.field-label {
  display: block;
  margin-top: 1rem;
  font-size: 0.875rem;
  font-weight: 600;
}
.amount-input {
  margin-top: 0.35rem;
  font-size: 1.25rem;
}
.err {
  margin: 0.5rem 0 0;
  color: var(--danger, #f87171);
  font-size: 0.9rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  justify-content: flex-end;
}
</style>
