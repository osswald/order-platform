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
      :style="cellStyle(cell)"
      :disabled="!cellEnabled(cell)"
      @click="onCellClick(cell)"
    >
      <span class="cell-label">{{ cell.label || '·' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { showToast } from '@/store'
import type { EdgeBundleEvent } from '@/types/api'
import { formatMoney, lineUnitCents } from '@/utils/money'
import {
  articlesForIds,
  fixedAmountVouchersForCell,
} from '@/utils/bundleHelpers'
import { textColorForBackground } from '@vendiqo/frontend-shared/colorContrast'

interface LayoutCell {
  col: number
  row: number
  color?: string
  label?: string
  article_ids?: number[]
  voucher_definition_uuids?: string[]
  voucher_definition_uuid?: string
}

interface AppLayout {
  grid_width?: number
  grid_height?: number
  cells?: LayoutCell[]
}

interface VoucherDefinition {
  uuid: string
  name?: string
  kind?: string
  value_cents?: number
}

interface PickItemArticle {
  key: string
  type: 'article'
  article_id: number
  label: string
  priceLabel: string
}

interface PickItemVoucher {
  key: string
  type: 'voucher'
  voucher: VoucherDefinition
  label: string
  priceLabel: string
}

type PickItem = PickItemArticle | PickItemVoucher

const props = defineProps<{
  layout: AppLayout
  event: EdgeBundleEvent
}>()

const emit = defineEmits<{
  pick: [articleIds: number[]]
  'pick-voucher': [voucher: VoucherDefinition]
  'pick-cell': [payload: { cell: LayoutCell; items: PickItem[] }]
}>()

function cellArticleIds(cell: LayoutCell) {
  const ids = cell.article_ids || []
  const arts = articlesForIds(props.event, ids)
  return arts.map((a) => a.id)
}

function cellEnabled(cell: LayoutCell) {
  return fixedAmountVouchersForCell(props.event, cell).length > 0 || cellArticleIds(cell).length > 0
}

function cellStyle(cell: LayoutCell) {
  const background = cell.color || '#334155'
  return {
    gridColumn: cell.col + 1,
    gridRow: cell.row + 1,
    background,
    color: textColorForBackground(background),
  }
}

function buildPickItems(cell: LayoutCell): PickItem[] {
  const items = []
  const arts = props.event?.articles || {}
  for (const vd of fixedAmountVouchersForCell(props.event, cell)) {
    const voucher = vd as unknown as VoucherDefinition
    const cents = Math.max(0, Number(voucher.value_cents) || 0)
    items.push({
      key: `voucher-${voucher.uuid}`,
      type: 'voucher' as const,
      voucher,
      label: `Gutschein: ${voucher.name || 'Gutschein'}`,
      priceLabel: formatMoney(cents, props.event.currency || 'CHF'),
    })
  }
  for (const id of cellArticleIds(cell)) {
    const a = arts[String(id)] || arts[id]
    const unit = lineUnitCents({ article_id: id, qty: 1, additions: [] }, arts, props.event)
    items.push({
      key: `article-${id}`,
      type: 'article' as const,
      article_id: id,
      label: a?.name || `Artikel #${id}`,
      priceLabel: formatMoney(unit, props.event.currency || 'CHF'),
    })
  }
  return items.sort((a, b) => {
    const nameA = a.type === 'voucher' ? (a.voucher?.name || 'Gutschein') : (a.label || '')
    const nameB = b.type === 'voucher' ? (b.voucher?.name || 'Gutschein') : (b.label || '')
    return String(nameA).localeCompare(String(nameB), 'de')
  })
}

function onCellClick(cell: LayoutCell) {
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
