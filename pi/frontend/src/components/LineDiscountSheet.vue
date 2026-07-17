<template>
  <Teleport to="body">
    <div v-if="open" class="discount-overlay">
      <div class="sheet-backdrop" @click.self="closeSheet" />
      <div class="sheet sheet--discount" role="dialog" aria-modal="true" @click.stop>
        <header class="sheet-header">
          <h3>{{ lineName }}</h3>
          <p class="muted sheet-sub">{{ formatMoney(lineGross, currency) }}</p>
        </header>

        <div class="discount-tabs">
          <button
            type="button"
            class="tab-btn"
            :class="{ active: mode === 'percent' }"
            @click.stop="mode = 'percent'"
          >
            Prozent
          </button>
          <button
            type="button"
            class="tab-btn"
            :class="{ active: mode === 'amount' }"
            @click.stop="mode = 'amount'"
          >
            Fixbetrag
          </button>
        </div>

        <template v-if="mode === 'percent'">
          <div class="chip-row">
            <button
              v-for="p in percentPresets"
              :key="p"
              type="button"
              class="chip-btn"
              :class="{ active: draftPercent === p && !customPercent }"
              @click.stop="pickPercent(p)"
            >
              {{ p }}%
            </button>
            <button
              type="button"
              class="chip-btn"
              :class="{ active: customPercent }"
              @click.stop="customPercent = true"
            >
              Andere
            </button>
          </div>
          <div v-if="customPercent" class="percent-input-row">
            <input
              v-model.number="draftPercent"
              type="number"
              min="0"
              max="100"
              class="text-input"
              inputmode="numeric"
            />
            <span>%</span>
          </div>
        </template>

        <template v-else>
          <MoneyKeypad v-model="draftAmountCents" :currency="currency" />
          <p class="muted hint">Max. {{ formatMoney(lineGross, currency) }}</p>
        </template>

        <p class="preview-row">
          Netto: <strong>{{ formatMoney(previewNet, currency) }}</strong>
        </p>

        <div class="sheet-actions">
          <button
            v-if="hasExisting"
            type="button"
            class="btn danger"
            @click.stop="removeDiscount"
          >
            Rabatt entfernen
          </button>
          <button type="button" class="btn" @click.stop="closeSheet">Abbrechen</button>
          <button
            type="button"
            class="btn primary"
            :disabled="!canApply"
            @click.stop="submitDiscount"
          >
            Übernehmen
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DiscountIn, EdgeBundleArticle, EdgeBundleEvent } from '@/types/api'
import type { CartLine } from '@/types/cart'
import MoneyKeypad from './MoneyKeypad.vue'
import {
  applyDiscountCents,
  formatMoney,
  lineGrossCents,
  normalizeDiscount,
} from '@/utils/money'
import { cartLineLabelForEvent } from '@/utils/bundleHelpers'

const props = withDefaults(
  defineProps<{
    open?: boolean
    line?: CartLine | null
    articles?: Record<string, EdgeBundleArticle>
    event?: EdgeBundleEvent | null
    currency?: string
  }>(),
  {
    open: false,
    line: null,
    articles: () => ({}),
    event: null,
    currency: 'CHF',
  },
)

const emit = defineEmits<{
  close: []
  'discount-save': [payload: { lineId: string; discount: DiscountIn | null }]
}>()

const mode = ref('percent')
const draftPercent = ref(10)
const customPercent = ref(false)
const draftAmountCents = ref(0)

const percentPresets = [5, 10, 15, 20]

const lineName = computed(() =>
  props.line ? cartLineLabelForEvent(props.line, props.event) : '',
)

const lineGross = computed(() => {
  if (!props.line) return 0
  return lineGrossCents(props.line, props.articles, props.event)
})

const hasExisting = computed(() => Boolean(normalizeDiscount(props.line?.discount)))

const draftDiscount = computed((): DiscountIn | null => {
  if (mode.value === 'percent') {
    const v = Math.max(0, Math.min(100, Number(draftPercent.value) || 0))
    if (v <= 0) return null
    return { kind: 'percent', value: v }
  }
  const v = Math.max(0, Math.min(lineGross.value, Number(draftAmountCents.value) || 0))
  if (v <= 0) return null
  return { kind: 'amount', value: v }
})

const previewNet = computed(() => {
  if (!props.line || !draftDiscount.value) return lineGross.value
  return applyDiscountCents(lineGross.value, draftDiscount.value)
})

const canApply = computed(() => Boolean(draftDiscount.value) && Boolean(props.line?.lineId))

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen || !props.line) return
    const d = normalizeDiscount(props.line.discount)
    if (d?.kind === 'amount') {
      mode.value = 'amount'
      draftAmountCents.value = d.value
      customPercent.value = false
    } else {
      mode.value = 'percent'
      draftPercent.value = d?.value ?? 10
      customPercent.value = d ? !percentPresets.includes(d.value) : false
      draftAmountCents.value = 0
    }
  },
)

function pickPercent(p: number) {
  customPercent.value = false
  draftPercent.value = p
}

function closeSheet() {
  emit('close')
}

function removeDiscount() {
  const lineId = props.line?.lineId
  if (!lineId) return
  emit('discount-save', { lineId, discount: null })
  emit('close')
}

function submitDiscount() {
  const lineId = props.line?.lineId
  const discount = draftDiscount.value
  if (!lineId || !discount) return
  emit('discount-save', { lineId, discount })
  emit('close')
}
</script>

<style scoped>
.discount-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  pointer-events: auto;
}
.discount-overlay .sheet-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 0;
}
.discount-overlay .sheet {
  position: relative;
  z-index: 1;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 70vh;
  overflow: auto;
  background: var(--card);
  border-radius: 1rem 1rem 0 0;
  padding: 1rem;
  padding-bottom: calc(1rem + var(--safe-bottom));
  border-top: 1px solid var(--border);
}
.sheet-sub {
  margin: 0.25rem 0 0;
  font-size: 0.95rem;
}
.discount-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.tab-btn {
  flex: 1;
  padding: 0.55rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.tab-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.chip-btn {
  min-width: 3.25rem;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.chip-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.percent-input-row span {
  color: var(--text);
}
.percent-input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.percent-input-row input {
  flex: 1;
  color: var(--text);
  background: var(--bg);
}
.hint {
  font-size: 0.85rem;
  margin-top: 0.35rem;
}
.preview-row {
  margin: 0.75rem 0;
  font-size: 1rem;
  color: var(--text);
}
.sheet--discount .sheet-header h3 {
  color: var(--text);
}
.sheet-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.sheet-actions .btn.danger {
  color: #b91c1c;
  border-color: #fecaca;
}
</style>
