<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import type { EdgeBundleEvent, KitchenOrderTicket, KitchenTicketLineEntry } from '@/types/api'
import {
  computeKitchenColumnLayout,
  KITCHEN_MIN_COLUMN_WIDTH_PX,
} from '@/utils/kitchenMonitorHelpers'
import KitchenTicketColumn from './KitchenTicketColumn.vue'

defineProps<{
  orders: KitchenOrderTicket[]
  event: EdgeBundleEvent | null | undefined
  busyTicketId: number | null
  selectedQty: (lineId: number) => number
}>()

const emit = defineEmits<{
  cycleLine: [line: KitchenTicketLineEntry]
  partialPrint: [ticket: KitchenOrderTicket]
  completePrint: [ticket: KitchenOrderTicket]
}>()

const containerRef = ref<HTMLElement | null>(null)
const ticketWidthPx = ref(KITCHEN_MIN_COLUMN_WIDTH_PX)
let resizeObserver: ResizeObserver | null = null

function updateColumnWidth() {
  const el = containerRef.value
  if (!el) return
  ticketWidthPx.value = computeKitchenColumnLayout(el.clientWidth).columnWidthPx
}

onMounted(() => {
  updateColumnWidth()
  const el = containerRef.value
  if (!el || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => {
    updateColumnWidth()
  })
  resizeObserver.observe(el)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<template>
  <div
    ref="containerRef"
    class="order-columns"
    :style="{ '--ticket-width': `${ticketWidthPx}px` }"
  >
    <p v-if="!orders.length" class="empty">Keine offenen Bestellungen.</p>
    <div v-for="ticket in orders" :key="ticket.id" class="order-slot">
      <KitchenTicketColumn
        :ticket="ticket"
        :event="event"
        :busy="busyTicketId === ticket.id"
        :selected-qty="selectedQty"
        @cycle-line="emit('cycleLine', $event)"
        @partial-print="emit('partialPrint', ticket)"
        @complete-print="emit('completePrint', ticket)"
      />
    </div>
  </div>
</template>

<style scoped>
.order-columns {
  --order-gap: 0.5rem;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  column-width: var(--ticket-width);
  column-gap: var(--order-gap);
  column-fill: auto;
}

.order-slot {
  break-inside: avoid;
  margin-bottom: var(--order-gap);
}

.empty {
  column-span: all;
  text-align: center;
  color: var(--muted);
  margin-top: 3rem;
  font-size: 1.1rem;
}
</style>
