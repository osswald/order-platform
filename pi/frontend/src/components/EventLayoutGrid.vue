<template>
  <div
    class="grid"
    :style="{
      gridTemplateColumns: `repeat(${layout.grid_width}, 1fr)`,
      gridTemplateRows: `repeat(${layout.grid_height}, minmax(48px, auto))`,
    }"
  >
    <button
      v-for="(cell, idx) in layout.cells"
      :key="idx"
      type="button"
      class="cell"
      :style="{
        gridColumn: cell.col + 1,
        gridRow: cell.row + 1,
        background: cell.color || '#334155',
      }"
      :disabled="!cellEnabled(cell)"
      @click="onCellClick(cell)"
    >
      <span class="cell-label">{{ cell.label || '·' }}</span>
    </button>
  </div>
</template>

<script setup>
import { showToast } from '../store'
import { formatAmount, lineUnitCents } from '../utils/money'
import {
  articlesForIds,
  cellVoucherUuids,
  fixedAmountVouchersForCell,
} from '../utils/bundleHelpers'

const props = defineProps({
  layout: { type: Object, required: true },
  event: { type: Object, required: true },
})

const emit = defineEmits(['pick', 'pick-voucher', 'pick-cell'])

function cellArticleIds(cell) {
  const ids = cell.article_ids || []
  const arts = articlesForIds(props.event, ids)
  return arts.map((a) => a.id)
}

function cellEnabled(cell) {
  return fixedAmountVouchersForCell(props.event, cell).length > 0 || cellArticleIds(cell).length > 0
}

function buildPickItems(cell) {
  const items = []
  const arts = props.event?.articles || {}
  for (const vd of fixedAmountVouchersForCell(props.event, cell)) {
    const cents = Math.max(0, Number(vd.value_cents) || 0)
    items.push({
      key: `voucher-${vd.uuid}`,
      type: 'voucher',
      voucher: vd,
      label: `Gutschein: ${vd.name || 'Gutschein'}`,
      priceLabel: formatAmount(cents),
    })
  }
  for (const id of cellArticleIds(cell)) {
    const a = arts[String(id)] || arts[id]
    const unit = lineUnitCents({ article_id: id, qty: 1, additions: [] }, arts, props.event)
    items.push({
      key: `article-${id}`,
      type: 'article',
      article_id: id,
      label: a?.name || `Artikel #${id}`,
      priceLabel: formatAmount(unit),
    })
  }
  return items
}

function onCellClick(cell) {
  const items = buildPickItems(cell)
  if (!items.length) {
    showToast('Zelle ohne verkaufbare Inhalte', 'err')
    return
  }
  if (items.length === 1) {
    const one = items[0]
    if (one.type === 'voucher') emit('pick-voucher', one.voucher)
    else emit('pick', [one.article_id])
    return
  }
  emit('pick-cell', { cell, items })
}
</script>

<style scoped>
.grid {
  display: grid;
  gap: 6px;
  width: 100%;
}
.cell {
  border: none;
  border-radius: 0.5rem;
  color: #0f172a;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.35rem;
  min-height: 48px;
  touch-action: manipulation;
}
.cell:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.cell-label {
  display: block;
  line-height: 1.2;
  word-break: break-word;
}
</style>
