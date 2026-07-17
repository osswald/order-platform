<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" @click.self="$emit('cancel')" />
    <div v-if="open" class="sheet sheet--picker" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>Zusätze</h3>
        <p class="muted">{{ articleName }}</p>
      </header>
      <SheetScrollBody :active="open">
        <ul class="sheet-option-list">
          <li v-for="a in sortedAdditions" :key="a.article_id" class="sheet-option-row">
            <label class="sheet-option-row__control">
              <input
                type="checkbox"
                :checked="selected.has(a.article_id)"
                :disabled="!canSelect(a)"
                @change="toggle(a)"
              />
              <span class="sheet-option-row__name">{{ a.name }}</span>
              <span class="sheet-option-row__meta">{{ priceHint(a) }}</span>
              <span v-if="isSoldOut(a)" class="badge">ausverkauft</span>
              <span v-else-if="stockHint(a)" class="stock-hint">{{ stockHint(a) }}</span>
            </label>
          </li>
        </ul>
      </SheetScrollBody>
      <div class="sheet__actions">
        <button type="button" class="btn" @click="$emit('cancel')">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirm">Übernehmen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EdgeBundleArticleAddition } from '@/types/api'
import { formatMoney } from '@/utils/money'
import { isAdditionSellable } from '@/store'
import SheetScrollBody from './SheetScrollBody.vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    articleName?: string
    additions?: EdgeBundleArticleAddition[]
    currency?: string
  }>(),
  { open: false, articleName: '', additions: () => [], currency: 'EUR' },
)

const emit = defineEmits<{
  cancel: []
  confirm: [additions: Array<{ article_id: number; qty: number }>]
}>()

const sortedAdditions = computed(() =>
  props.additions
    .slice()
    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'de')),
)

const selected = ref<Set<number>>(new Set())

watch(
  () => props.open,
  (o) => {
    if (!o) return
    const ids = props.additions
      .filter((a) => a.preselected && canSelect(a))
      .map((a) => Number(a.article_id))
    selected.value = new Set(ids)
  },
  { immediate: true },
)

function priceHint(a: EdgeBundleArticleAddition) {
  const p = Number(a.price) || 0
  if (p === 0) return 'inkl.'
  const cents = Math.round(p * 100)
  return formatMoney(cents, props.currency)
}

function isSoldOut(a: EdgeBundleArticleAddition) {
  return !isAdditionSellable(a.article_id, null, a)
}

function stockHint(a: EdgeBundleArticleAddition): string | null {
  if (isSoldOut(a)) return null
  if (!a.monitor_stock) return null
  return `${a.in_stock ?? 0} Stk.`
}

function canSelect(a: EdgeBundleArticleAddition) {
  return isAdditionSellable(a.article_id, null, a)
}

function toggle(a: EdgeBundleArticleAddition) {
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
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
}
.sheet-header h3 {
  margin: 0;
}
.sheet-option-row__control {
  flex-wrap: wrap;
  cursor: pointer;
}
.sheet-option-row__control input {
  width: 1.25rem;
  height: 1.25rem;
}
.badge {
  font-size: 0.75rem;
  color: var(--danger);
}
.stock-hint {
  font-size: 0.75rem;
  color: var(--muted);
}
.sheet__actions {
  display: flex;
  gap: 0.5rem;
}
.sheet__actions .btn {
  flex: 1;
}
</style>
