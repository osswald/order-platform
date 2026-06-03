<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="onCancel" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true" aria-labelledby="pay-type-title">
      <header class="sheet-header">
        <h3 id="pay-type-title">Zahlungsart</h3>
        <p v-if="amountLabel" class="muted">Betrag: {{ amountLabel }}</p>
      </header>
      <div class="type-buttons">
        <div v-for="entry in normalizedTypes" :key="entry.value" class="type-btn-wrap">
          <button
            type="button"
            class="btn type-btn primary"
            :class="{ 'type-btn--disabled': entry.disabled }"
            :disabled="entry.disabled"
            @click="onSelect(entry)"
          >
            {{ label(entry.value) }}
          </button>
          <p v-if="entry.disabled && entry.hint" class="type-hint muted">{{ entry.hint }}</p>
        </div>
      </div>
      <div class="sheet-actions">
        <button type="button" class="btn" @click="onCancel">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { paymentTypeLabel } from '../utils/paymentTypes'

const props = defineProps({
  open: Boolean,
  types: { type: Array, default: () => [] },
  amountLabel: { type: String, default: '' },
})

const emit = defineEmits(['select', 'cancel'])

const normalizedTypes = computed(() =>
  (props.types || []).map((t) => {
    if (typeof t === 'object' && t != null) {
      return {
        value: t.value,
        disabled: Boolean(t.disabled),
        hint: t.hint || '',
      }
    }
    return { value: t, disabled: false, hint: '' }
  }),
)

function label(t) {
  return paymentTypeLabel(t)
}

function onSelect(entry) {
  if (entry.disabled) return
  emit('select', entry.value)
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
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
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
.type-btn-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.type-btn {
  width: 100%;
  min-height: 52px;
  font-size: 1.1rem;
  font-weight: 700;
}
.type-btn--disabled,
.type-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.type-hint {
  margin: 0;
  font-size: 0.85rem;
  padding-left: 0.25rem;
}
.sheet-actions .btn {
  width: 100%;
  min-height: 44px;
}
</style>
