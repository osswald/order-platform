<template>
  <li class="split-line" :class="variant">
    <template v-if="variant === 'top'">
      <button type="button" class="cell qty" @click.stop="$emit('tap-qty')">{{ basketQty }}</button>
      <button type="button" class="cell name" @click.stop="$emit('tap-name')">
        <span class="name-text">{{ name }}</span>
        <span v-for="add in additionLabels" :key="add.id" class="addition">+ {{ add.name }}</span>
      </button>
      <button type="button" class="cell price" @click.stop="$emit('tap-price')">{{ lineTotal }}</button>
    </template>
    <template v-else>
      <button type="button" class="row-btn" @click="$emit('tap-row')">
        <span class="ratio">{{ remainingQty }} / {{ totalQty }}</span>
        <span class="name-col">
          <span class="name-text">{{ name }}</span>
          <span v-for="add in additionLabels" :key="add.id" class="addition">+ {{ add.name }}</span>
        </span>
        <span class="price">{{ lineTotal }}</span>
      </button>
    </template>
  </li>
</template>

<script setup>
import { computed } from 'vue'
import { formatAmount } from '../utils/money'

const props = defineProps({
  variant: { type: String, default: 'bottom' },
  name: { type: String, required: true },
  additionLabels: { type: Array, default: () => [] },
  basketQty: { type: Number, default: 0 },
  totalQty: { type: Number, default: 0 },
  unitCents: { type: Number, default: 0 },
})

defineEmits(['tap-qty', 'tap-name', 'tap-price', 'tap-row'])

const remainingQty = computed(() => Math.max(0, props.totalQty - props.basketQty))

const lineTotal = computed(() => {
  const q = props.variant === 'top' ? props.basketQty : remainingQty.value
  return formatAmount(props.unitCents * Math.max(0, q))
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
.price {
  font-variant-numeric: tabular-nums;
}
</style>
