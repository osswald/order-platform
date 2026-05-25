<template>
  <div class="cart-panel">
    <p v-if="!lines.length" class="cart-empty">Artikel unten antippen</p>
    <ul v-else class="cart-lines">
      <li v-for="l in lines" :key="l.lineId" class="cart-line">
        <button type="button" class="cart-cell cart-qty" @click="$emit('tap-qty', l)">
          {{ l.qty }}
        </button>
        <button type="button" class="cart-cell cart-name" @click="$emit('tap-name', l)">
          <span class="cart-name-text">{{ label(l) }}</span>
          <span v-for="add in lineAdditions(l)" :key="add.id" class="cart-addition">+ {{ add.name }}</span>
        </button>
        <button type="button" class="cart-cell cart-price" @click="$emit('tap-price', l.lineId)">
          {{ formatLine(l) }}
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { lineTotalCents, formatMoney } from '../utils/money'

const props = defineProps({
  lines: { type: Array, default: () => [] },
  articles: { type: Object, default: () => ({}) },
  currency: { type: String, default: 'EUR' },
  labelFn: { type: Function, default: null },
})

defineEmits(['tap-qty', 'tap-name', 'tap-price'])

function label(line) {
  if (props.labelFn) return props.labelFn(line)
  const id = line.article_id
  const a = props.articles[String(id)] || props.articles[id]
  return a?.name || `#${id}`
}

function lineAdditions(line) {
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
  return formatMoney(lineTotalCents(l, props.articles), props.currency)
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
.cart-addition {
  display: block;
  padding-left: 0.65rem;
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 400;
}
</style>
