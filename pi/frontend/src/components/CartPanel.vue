<template>
  <div ref="panelRef" class="cart-panel">
    <p v-if="!lines.length && !orderDiscountRow" class="cart-empty">Artikel unten antippen</p>
    <ul v-else class="cart-lines">
      <li v-for="l in lines" :key="l.lineId" class="cart-line">
        <button type="button" class="cart-cell cart-qty" @click="$emit('tap-qty', l)">
          {{ l.qty }}
        </button>
        <button type="button" class="cart-cell cart-name" @click="$emit('tap-name', l)">
          <span class="cart-name-text">{{ lineLabel(l) }}</span>
          <span v-for="add in lineAdditions(l)" :key="add.id" class="cart-addition">+ {{ add.name }}</span>
          <span v-if="lineHasNote(l)" class="cart-note-hint">{{ l.note }}</span>
          <template v-if="lineHasDiscount(l)">
            <span class="cart-discount-hint">{{ lineDiscountHint(l) }}</span>
            <span class="cart-discount-prices">
              <span class="cart-price-gross">{{ formatGross(l) }}</span>
              <span class="cart-price-arrow" aria-hidden="true">→</span>
              <span class="cart-price-net">{{ formatLine(l) }}</span>
            </span>
          </template>
        </button>
        <div
          v-if="showLineCommentBtn(l) || showLineDiscountBtn(l)"
          class="cart-line-actions"
        >
          <button
            v-if="showLineCommentBtn(l)"
            type="button"
            class="cart-cell cart-action-btn cart-comment-btn"
            :class="{ 'cart-action-btn--active': lineHasNote(l) }"
            aria-label="Kommentar"
            @click="$emit('tap-comment', l)"
          >
            <svg class="cart-action-icon" viewBox="0 0 16 16" aria-hidden="true">
              <path
                fill="currentColor"
                d="M2 2.5A1.5 1.5 0 0 1 3.5 1h9A1.5 1.5 0 0 1 14 2.5v6A1.5 1.5 0 0 1 12.5 10H8l-3.5 3v-3H3.5A1.5 1.5 0 0 1 2 8.5v-6Z"
              />
            </svg>
          </button>
          <button
            v-if="showLineDiscountBtn(l)"
            type="button"
            class="cart-cell cart-action-btn cart-discount-btn"
            :class="{ 'cart-action-btn--active': lineHasDiscount(l) }"
            aria-label="Rabatt"
            @click="$emit('tap-discount', l)"
          >
            {{ discountBtnLabel(l) }}
          </button>
        </div>
        <button type="button" class="cart-cell cart-price" @click="$emit('tap-price', l.lineId)">
          {{ formatLine(l) }}
        </button>
      </li>
      <li v-if="orderDiscountRow" class="cart-line cart-line--order-discount">
        <span class="cart-order-discount-label">{{ orderDiscountRow.label }}</span>
        <button type="button" class="cart-order-discount-remove" @click="$emit('remove-order-discount')">
          ×
        </button>
        <span class="cart-order-discount-amount">{{ orderDiscountRow.amount }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  applyDiscountCents,
  discountButtonLabel,
  discountLabel,
  formatMoney,
  lineGrossCents,
  lineTotalCents,
  normalizeDiscount,
  orderSubtotalCents,
} from '../utils/money'
import { cartLineLabelForEvent } from '../utils/bundleHelpers'

const props = defineProps({
  lines: { type: Array, default: () => [] },
  articles: { type: Object, default: () => ({}) },
  event: { type: Object, default: null },
  currency: { type: String, default: 'EUR' },
  labelFn: { type: Function, default: null },
  discountsEnabled: { type: Boolean, default: false },
  positionCommentsEnabled: { type: Boolean, default: false },
  orderDiscount: { type: Object, default: null },
})

defineEmits(['tap-qty', 'tap-name', 'tap-price', 'tap-discount', 'tap-comment', 'remove-order-discount'])

const panelRef = ref(null)
let prevLineCount = 0

watch(
  () => props.lines.length,
  (count) => {
    if (count > prevLineCount) {
      nextTick(() => {
        const el = panelRef.value
        if (el) el.scrollTop = el.scrollHeight
      })
    }
    prevLineCount = count
  },
  { immediate: true },
)

const orderDiscountRow = computed(() => {
  if (!props.discountsEnabled || !props.orderDiscount) return null
  const off = orderDiscountOff.value
  if (off <= 0) return null
  return {
    label: 'Rabatt Bestellung',
    amount: `−${formatMoney(off, props.currency)}`,
  }
})

const orderDiscountOff = computed(() => {
  const sub = orderSubtotalCents(props.lines, props.articles, props.event)
  const total = applyDiscountCents(sub, props.orderDiscount)
  return Math.max(0, sub - total)
})

function lineLabel(line) {
  if (props.labelFn) return props.labelFn(line)
  return cartLineLabelForEvent(line, props.event)
}

function showLineDiscountBtn(line) {
  return props.discountsEnabled && line?.kind !== 'voucher_sale'
}

function showLineCommentBtn(line) {
  return props.positionCommentsEnabled && line?.kind !== 'voucher_sale'
}

function lineHasNote(line) {
  return Boolean(String(line?.note || '').trim())
}

function lineHasDiscount(line) {
  return Boolean(normalizeDiscount(line?.discount))
}

function lineDiscountHint(line) {
  if (!lineHasDiscount(line)) return ''
  return discountLabel(line.discount)
}

function discountBtnLabel(line) {
  return discountButtonLabel(line.discount)
}

function lineAdditions(line) {
  if (line?.kind === 'voucher_sale') return []
  const base = props.articles[String(line.article_id)] || props.articles[line.article_id]
  const out = []
  for (const add of line.additions || []) {
    const id = add.article_id
    let name = `#${id}`
    const fromLine = (base?.additions || []).find((x) => Number(x.article_id) === Number(id))
    if (fromLine?.name) name = fromLine.name
    else {
      const a = props.articles[String(id)] || props.articles[id]
      if (a?.name) name = a.name
    }
    out.push({ id, name })
  }
  return out
}

function formatLine(l) {
  return formatMoney(lineTotalCents(l, props.articles, props.event), props.currency)
}

function formatGross(l) {
  return formatMoney(lineGrossCents(l, props.articles, props.event), props.currency)
}
</script>

<style scoped>
.cart-name.cart-cell {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
}
.cart-name-text {
  font-weight: 500;
}
.cart-discount-hint,
.cart-note-hint,
.cart-discount-prices {
  display: block;
  padding-left: 0.65rem;
  font-size: 0.8rem;
  font-weight: 400;
}
.cart-discount-hint {
  color: var(--muted);
  margin-top: 0.1rem;
}
.cart-discount-prices {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.cart-price-gross {
  text-decoration: line-through;
}
.cart-price-arrow {
  margin: 0 0.2rem;
}
.cart-price-net {
  color: #111;
  font-weight: 600;
}
.cart-addition {
  display: block;
  padding-left: 0.65rem;
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 400;
}
.cart-line-actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  flex-shrink: 0;
  padding: 0.35rem 0.15rem 0.35rem 0;
}
.cart-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  width: 2rem;
  height: 2rem;
  padding: 0;
  flex-shrink: 0;
  text-align: center;
  font-weight: 700;
  font-size: 0.85rem;
  line-height: 1;
  color: #64748b;
  border-radius: 0.35rem;
}
.cart-action-btn--active {
  background: var(--accent);
  color: #fff;
}
.cart-discount-btn {
  min-width: 2.25rem;
  width: auto;
  max-width: 3.25rem;
  padding: 0 0.25rem;
}
.cart-action-icon {
  width: 0.95rem;
  height: 0.95rem;
}
.cart-price {
  align-self: center;
}
.cart-line--order-discount {
  display: flex;
  align-items: center;
  padding: 0.55rem 0.5rem;
  background: #f8fafc;
  font-weight: 600;
}
.cart-order-discount-label {
  flex: 1;
}
.cart-order-discount-remove {
  border: none;
  background: transparent;
  font-size: 1.25rem;
  line-height: 1;
  padding: 0 0.5rem;
  cursor: pointer;
  color: var(--muted);
}
.cart-order-discount-amount {
  font-variant-numeric: tabular-nums;
  color: #b45309;
}
</style>
