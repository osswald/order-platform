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
      :disabled="!cellArticleIds(cell).length"
      @click="$emit('pick', cellArticleIds(cell))"
    >
      <span class="cell-label">{{ cell.label || '·' }}</span>
    </button>
  </div>
</template>

<script setup>
import { articlesForIds } from '../utils/bundleHelpers'

const props = defineProps({
  layout: { type: Object, required: true },
  event: { type: Object, required: true },
})

defineEmits(['pick'])

function cellArticleIds(cell) {
  const ids = cell.article_ids || []
  const arts = articlesForIds(props.event, ids)
  return arts.map((a) => a.id)
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
