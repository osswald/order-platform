<template>
  <div
    v-if="shiftCloseDialogOpen"
    class="shift-overlay"
    role="dialog"
    aria-modal="true"
  >
    <div class="shift-card">
      <h2>Schicht beenden</h2>
      <p class="muted">Kassenbestand zählen (CHF)</p>
      <p v-if="shiftCloseExpectedLabel" class="muted expected">
        Erwartet ca. {{ shiftCloseExpectedLabel }}
      </p>
      <p class="field-label">Betrag (CHF)</p>
      <MoneyKeypad v-model="amountCents" currency="CHF" />
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
import MoneyKeypad from '@/components/MoneyKeypad.vue'
import {
  cancelShiftClose,
  confirmShiftClose,
  formatCentsChf,
  shiftCloseAmountChf,
  shiftCloseDialogOpen,
  shiftCloseError,
  shiftCloseExpectedLabel,
} from '@/composables/useShiftSession'

const amountCents = computed({
  get() {
    const n = parseFloat(String(shiftCloseAmountChf.value || '').replace(',', '.'))
    if (Number.isNaN(n) || n < 0) return 0
    return Math.round(n * 100)
  },
  set(cents: number) {
    shiftCloseAmountChf.value = formatCentsChf(cents)
  },
})
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
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 600;
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
