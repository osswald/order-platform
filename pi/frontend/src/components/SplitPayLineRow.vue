<template>
  <li class="split-line" :class="variant">
    <template v-if="variant === 'top'">
      <button type="button" class="cell qty" @click.stop="$emit('tap-qty')">{{ basketQty }}</button>
      <button type="button" class="cell name" @click.stop="$emit('tap-name')">
        <span class="name-text">{{ name }}</span>
        <span v-for="add in additionLabels" :key="add.id" class="addition">+ {{ add.name }}</span>
        <template v-if="hasDiscount">
          <span class="discount-hint">{{ discountHint }}</span>
          <span class="discount-prices">
            <span class="price-gross">{{ formatGrossTotal }}</span>
            <span class="price-arrow" aria-hidden="true">→</span>
            <span class="price-net">{{ lineTotal }}</span>
          </span>
        </template>
      </button>
      <button type="button" class="cell price" @click.stop="$emit('tap-price')">{{ lineTotal }}</button>
    </template>
    <template v-else>
      <button type="button" class="row-btn" @click="$emit('tap-row')">
        <span class="ratio">{{ remainingQty }} / {{ totalQty }}</span>
        <span class="name-col">
          <span class="name-text">{{ name }}</span>
          <span v-for="add in additionLabels" :key="add.id" class="addition">+ {{ add.name }}</span>
          <template v-if="hasDiscount">
            <span class="discount-hint">{{ discountHint }}</span>
            <span class="discount-prices">
              <span class="price-gross">{{ formatGrossTotal }}</span>
              <span class="price-arrow" aria-hidden="true">→</span>
              <span class="price-net">{{ lineTotal }}</span>
            </span>
          </template>
        </span>
        <span class="price">{{ lineTotal }}</span>
      </button>
    </template>
  </li>
</template>

<script setup>
import { computed } from 'vue'
import {
  discountLabel,
  formatAmount,
  lineGrossCents,
  lineTotalCents,
  normalizeDiscount,
} from '../utils/money'

const props = defineProps({
  variant: { type: String, default: 'bottom' },
  name: { type: String, required: true },
  additionLabels: { type: Array, default: () => [] },
  basketQty: { type: Number, default: 0 },
  totalQty: { type: Number, default: 0 },
  unitCents: { type: Number, default: 0 },
  lineTotalCents: { type: Number, default: 0 },
  discount: { type: Object, default: null },
  articles: { type: Object, default: () => ({}) },
  event: { type: Object, default: null },
})

defineEmits(['tap-qty', 'tap-name', 'tap-price', 'tap-row'])

const remainingQty = computed(() => Math.max(0, props.totalQty - props.basketQty))

const displayQty = computed(() =>
  props.variant === 'top' ? props.basketQty : remainingQty.value,
)

const lineForPricing = computed(() => ({
  article_id: 0,
  qty: Math.max(1, displayQty.value),
  unit_cents: props.unitCents,
  additions: [],
  discount: props.discount,
}))

function netCentsForQty(qty) {
  const q = Math.max(0, Number(qty) || 0)
  const totalQty = Math.max(1, Number(props.totalQty) || 1)
  const lineTotal = Math.max(0, Number(props.lineTotalCents) || 0)
  if (lineTotal > 0) {
    return Math.round((lineTotal / totalQty) * q)
  }
  const line = {
    article_id: 0,
    qty: Math.max(1, q),
    unit_cents: props.unitCents,
    additions: [],
    discount: props.discount,
  }
  return lineTotalCents(line, props.articles, props.event)
}

const lineTotal = computed(() => formatAmount(netCentsForQty(displayQty.value)))

const hasDiscount = computed(() => Boolean(normalizeDiscount(props.discount)))

const discountHint = computed(() => (hasDiscount.value ? discountLabel(props.discount) : ''))

const formatGrossTotal = computed(() => {
  const gross = lineGrossCents(lineForPricing.value, props.articles, props.event)
  return formatAmount(gross)
})
</script>

<style scoped>
.split-line {
  list-style: none;
  border-bottom: 1px solid #e2e8f0;
}
.split-line.top {
  display: flex;
  background: #fff;
  color: #111;
}
.split-line.top .cell {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.75rem 0.5rem;
  font-size: 1rem;
  text-align: left;
  cursor: pointer;
  touch-action: manipulation;
}
.split-line.top .qty {
  flex: 0 0 2.5rem;
  font-weight: 700;
  text-align: center;
}
.split-line.top .price {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.row-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.5rem;
  border: none;
  background: #fff;
  color: #111;
  font-size: 1rem;
  cursor: pointer;
  text-align: left;
  touch-action: manipulation;
}
.ratio {
  min-width: 3rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.name {
  flex: 1;
  text-align: left;
}
.name-col,
.split-line.top .name {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
}
.name-text {
  font-weight: 500;
}
.addition {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 400;
}
.discount-hint,
.discount-prices {
  display: block;
  padding-left: 0.65rem;
  font-size: 0.8rem;
  font-weight: 400;
}
.discount-hint {
  color: #64748b;
  margin-top: 0.1rem;
}
.discount-prices {
  color: #64748b;
  font-variant-numeric: tabular-nums;
}
.price-gross {
  text-decoration: line-through;
}
.price-arrow {
  margin: 0 0.2rem;
}
.price-net {
  color: #111;
  font-weight: 600;
}
.price {
  font-variant-numeric: tabular-nums;
}
</style>
