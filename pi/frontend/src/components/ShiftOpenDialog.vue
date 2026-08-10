<template>
  <div
    v-if="shiftOpenDialogOpen"
    class="shift-overlay"
    role="dialog"
    aria-modal="true"
  >
    <div class="shift-card">
      <h2>Schicht starten</h2>
      <p class="muted">Wechselgeld / Kassenbestand eingeben</p>
      <p class="field-label">Betrag (CHF)</p>
      <MoneyKeypad v-model="amountCents" currency="CHF" />
      <div class="actions">
        <button type="button" class="btn" @click="cancelShiftOpen">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirmShiftOpen">Start</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MoneyKeypad from '@/components/MoneyKeypad.vue'
import {
  shiftOpenDialogOpen,
  shiftOpenAmountChf,
  confirmShiftOpen,
  cancelShiftOpen,
  formatCentsChf,
} from '@/composables/useShiftSession'

const amountCents = computed({
  get() {
    const n = parseFloat(String(shiftOpenAmountChf.value || '').replace(',', '.'))
    if (Number.isNaN(n) || n < 0) return 0
    return Math.round(n * 100)
  },
  set(cents: number) {
    shiftOpenAmountChf.value = formatCentsChf(cents)
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
.field-label {
  display: block;
  margin-top: 1rem;
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  justify-content: flex-end;
}
</style>
