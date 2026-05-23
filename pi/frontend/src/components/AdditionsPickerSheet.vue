<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('cancel')" />
    <div v-if="open" class="sheet" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>Zusätze</h3>
        <p class="muted">{{ articleName }}</p>
      </header>
      <ul class="add-list">
        <li v-for="a in additions" :key="a.article_id" class="add-row">
          <label class="add-label">
            <input
              type="checkbox"
              :checked="selected.has(a.article_id)"
              :disabled="!canSelect(a)"
              @change="toggle(a)"
            />
            <span class="name">{{ a.name }}</span>
            <span class="price-hint">{{ priceHint(a) }}</span>
            <span v-if="a.monitor_stock && !a.sellable" class="badge">ausverkauft</span>
            <span v-else-if="a.monitor_stock" class="stock-hint">{{ a.in_stock ?? 0 }} Stk.</span>
          </label>
        </li>
      </ul>
      <div class="sheet-actions">
        <button type="button" class="btn" @click="$emit('cancel')">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirm">Übernehmen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { formatMoney } from '../utils/money'

const props = defineProps({
  open: Boolean,
  articleName: { type: String, default: '' },
  additions: { type: Array, default: () => [] },
  currency: { type: String, default: 'EUR' },
})

const emit = defineEmits(['cancel', 'confirm'])

const selected = ref(new Set())

watch(
  () => props.open,
  (o) => {
    if (o) selected.value = new Set()
  },
)

function priceHint(a) {
  const p = Number(a.price) || 0
  if (p === 0) return 'inkl.'
  const cents = Math.round(p * 100)
  return formatMoney(cents, props.currency)
}

function canSelect(a) {
  if (a.sellable === false) return false
  if (a.monitor_stock && (a.in_stock ?? 0) < 1) return false
  return true
}

function toggle(a) {
  const id = Number(a.article_id)
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else if (canSelect(a)) next.add(id)
  selected.value = next
}

function confirm() {
  const out = [...selected.value].map((article_id) => ({ article_id, qty: 1 }))
  emit('confirm', out)
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
  max-height: 70vh;
  overflow: auto;
}
.sheet-header h3 {
  margin: 0;
}
.add-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}
.add-row {
  border-bottom: 1px solid var(--border);
}
.add-label {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.85rem 0.25rem;
  cursor: pointer;
  width: 100%;
}
.add-label input {
  width: 1.25rem;
  height: 1.25rem;
}
.name {
  flex: 1;
  font-weight: 500;
}
.price-hint {
  font-variant-numeric: tabular-nums;
  color: var(--muted);
}
.badge {
  font-size: 0.75rem;
  color: var(--danger);
}
.stock-hint {
  font-size: 0.75rem;
  color: var(--muted);
}
.sheet-actions {
  display: flex;
  gap: 0.5rem;
}
.sheet-actions .btn {
  flex: 1;
}
</style>
