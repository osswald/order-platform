<script setup lang="ts">
import { computed } from 'vue'
import { textColorForBackground } from '@vendiqo/frontend-shared/colorContrast'
import type { KitchenProductRow, KitchenProductSummary } from '@/utils/kitchenProductSummary'
import { kitchenProductLocationShortLabel } from '@/utils/kitchenProductSummary'

const props = defineProps<{
  summary: KitchenProductSummary
  showAdditions: boolean
}>()

const rows = computed(() => [
  ...props.summary.articles.map((row) => ({ row, kind: 'article' as const })),
  ...(props.showAdditions
    ? props.summary.additions.map((row) => ({ row, kind: 'addition' as const }))
    : []),
])

function rowStyle(row: KitchenProductRow) {
  if (!row.color) return {}
  return {
    background: row.color,
    color: textColorForBackground(row.color),
  }
}
</script>

<template>
  <div class="product-list">
    <p v-if="!rows.length" class="empty">Keine offenen Produkte.</p>

    <article
      v-for="{ row, kind } in rows"
      :key="`${kind}-${row.key}`"
      class="product-card"
      :class="{ 'product-card--addition': kind === 'addition' }"
      :style="rowStyle(row)"
    >
      <div class="product-head">
        <span class="product-name">{{ row.name }}</span>
        <strong class="product-qty">{{ row.totalQty }}</strong>
      </div>

      <div v-if="row.breakdown.length" class="breakdown-wrap">
        <table class="breakdown-table">
          <tbody>
            <tr class="row-tisch">
              <th scope="row" class="axis-label">Tisch</th>
              <td v-for="part in row.breakdown" :key="`${row.key}-loc-${part.label}`">
                {{ kitchenProductLocationShortLabel(part.label) }}
              </td>
            </tr>
            <tr class="row-stk">
              <th scope="row" class="axis-label">Stk</th>
              <td v-for="part in row.breakdown" :key="`${row.key}-qty-${part.label}`">
                {{ part.qty }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </div>
</template>

<style scoped>
.product-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-content: flex-start;
  padding-bottom: 0.35rem;
}

.product-card {
  box-sizing: border-box;
  width: fit-content;
  max-width: 100%;
  border: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
  border-radius: 0.75rem;
  padding: 0.65rem 0.7rem 0.55rem;
  background: var(--card);
}

.product-card--addition {
  border-style: dashed;
}

.product-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.product-name {
  min-width: 0;
  font-size: 1.2rem;
  font-weight: 800;
  line-height: 1.1;
}

.product-qty {
  flex: 0 0 auto;
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
}

.breakdown-wrap {
  margin-top: 0.45rem;
}

.breakdown-table {
  width: auto;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.breakdown-table td,
.breakdown-table th {
  padding: 0.1rem 0.45rem;
  text-align: center;
  white-space: nowrap;
  border-left: 1px solid color-mix(in srgb, currentColor 28%, transparent);
}

.breakdown-table tr td:first-of-type,
.breakdown-table tr th.axis-label {
  border-left: none;
}

.breakdown-table .row-tisch th,
.breakdown-table .row-tisch td {
  padding-bottom: 0.25rem;
  border-bottom: 1px solid color-mix(in srgb, currentColor 32%, transparent);
}

.breakdown-table .row-stk th,
.breakdown-table .row-stk td {
  padding-top: 0.25rem;
}

.axis-label {
  padding-left: 0;
  padding-right: 0.55rem;
  text-align: left;
  text-decoration: underline;
  font-weight: 800;
}

.empty {
  width: 100%;
  text-align: center;
  color: var(--muted);
  margin-top: 3rem;
  font-size: 1.2rem;
}
</style>
