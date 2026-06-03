<template>
  <div v-if="shiftOpenDialogOpen" class="shift-overlay" role="dialog" aria-modal="true">
    <div class="shift-card">
      <h2>Schicht starten</h2>
      <p class="muted">Wechselgeld / Kassenbestand eingeben</p>
      <label class="field-label">
        Betrag (CHF)
        <input v-model="shiftOpenAmountChf" type="text" inputmode="decimal" class="input amount-input" />
      </label>
      <div class="actions">
        <button type="button" class="btn" @click="cancelShiftOpen">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirmShiftOpen">Start</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  shiftOpenDialogOpen,
  shiftOpenAmountChf,
  confirmShiftOpen,
  cancelShiftOpen,
} from '../composables/useShiftSession'
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
  font-size: 0.875rem;
  font-weight: 600;
}
.amount-input {
  margin-top: 0.35rem;
  font-size: 1.25rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  justify-content: flex-end;
}
</style>
