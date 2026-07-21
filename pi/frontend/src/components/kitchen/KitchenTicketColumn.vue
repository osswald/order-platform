<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { EdgeBundleEvent, KitchenOrderTicket, KitchenTicketLineEntry, OrderLineIn } from '@/types/api'
import {
  formatElapsedMinutes,
  kitchenLineAdditionLabels,
  ticketElapsedMs,
  ticketStatusLabel,
  ticketUrgencyLevel,
  type KitchenUrgencyLevel,
} from '@/utils/kitchenMonitorHelpers'
import { lineSelectionLabel } from '@/utils/kitchenLineSelection'

const props = defineProps<{
  ticket: KitchenOrderTicket
  event: EdgeBundleEvent | null | undefined
  busy: boolean
  selectedQty: (lineId: number) => number
}>()

const emit = defineEmits<{
  cycleLine: [line: KitchenTicketLineEntry]
  partialPrint: []
  completePrint: []
}>()

const nowMs = ref(Date.now())
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  timer = setInterval(() => {
    nowMs.value = Date.now()
  }, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const elapsedLabel = computed(() => formatElapsedMinutes(ticketElapsedMs(props.ticket, nowMs.value)))
const urgency = computed(() => ticketUrgencyLevel(props.ticket, nowMs.value))
const hasSelection = computed(() =>
  (props.ticket.lines || []).some((line) => props.selectedQty(line.id) > 0),
)

function lineName(line: OrderLineIn) {
  const withName = line as OrderLineIn & { article_name?: string | null }
  if (withName.article_name) return withName.article_name
  const aid = line?.article_id
  if (aid == null) return '#?'
  const article = props.event?.articles?.[String(aid)] || props.event?.articles?.[aid as unknown as string]
  return article?.name || `#${aid}`
}

function additionLabels(line: OrderLineIn) {
  return kitchenLineAdditionLabels(line, props.event?.articles)
}

function urgencyClass(level: KitchenUrgencyLevel) {
  return `urgency-${level}`
}

function locationLabel() {
  if (props.ticket.pickup_code) return `Pickup ${props.ticket.pickup_code}`
  return `Tisch ${props.ticket.table_number || '—'}`
}
</script>

<template>
  <article class="ticket-column" :class="{ busy }">
    <div class="urgency-bar" :class="urgencyClass(urgency)" />
    <header class="ticket-header">
      <div>
        <div class="ticket-title">{{ locationLabel() }}</div>
        <div class="ticket-sub">
          Bestellung #{{ ticket.order_number || ticket.id }}
          <span v-if="ticket.waiter_name"> · {{ ticket.waiter_name }}</span>
        </div>
      </div>
      <div class="ticket-meta">
        <span class="elapsed">{{ elapsedLabel }}</span>
        <span class="ticket-status">{{ ticketStatusLabel(ticket.status) }}</span>
      </div>
    </header>

    <ul class="line-list">
      <li
        v-for="line in ticket.lines"
        :key="line.id"
        class="line-row"
        :class="{ selected: selectedQty(line.id) > 0 }"
      >
        <button type="button" class="line-btn" :disabled="busy" @click="emit('cycleLine', line)">
          <strong>{{ lineSelectionLabel(line, selectedQty(line.id), lineName(line.line as OrderLineIn)) }}</strong>
          <span v-if="(line.line as OrderLineIn).note" class="line-note">{{ (line.line as OrderLineIn).note }}</span>
          <span
            v-for="(label, index) in additionLabels(line.line as OrderLineIn)"
            :key="`${line.id}-addition-${index}`"
            class="line-addition muted"
          >{{ label }}</span>
        </button>
      </li>
    </ul>

    <footer class="ticket-actions">
      <button type="button" class="btn action-btn partial-btn" :disabled="busy || !hasSelection" @click="emit('partialPrint')">
        Teildruck
      </button>
      <button type="button" class="btn action-btn complete-btn" :disabled="busy" @click="emit('completePrint')">
        Komplettdruck
      </button>
    </footer>
  </article>
</template>

<style scoped>
.ticket-column {
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
  max-width: var(--ticket-width, 300px);
  height: fit-content;
  border: 1px solid var(--border);
  border-radius: 0.9rem;
  background: var(--card);
  overflow: hidden;
}

.ticket-column.busy {
  opacity: 0.65;
  pointer-events: none;
}

.urgency-bar {
  height: 5px;
}

.urgency-green {
  background: #22c55e;
}

.urgency-amber {
  background: #f59e0b;
}

.urgency-red {
  background: #ef4444;
}

.ticket-header {
  padding: 0.7rem 0.85rem 0.6rem;
  border-bottom: 1px solid var(--border);
}

.ticket-title {
  font-size: 1.25rem;
  font-weight: 800;
  line-height: 1.1;
}

.ticket-sub,
.product-breakdown {
  color: var(--muted);
  font-size: 0.85rem;
}

.ticket-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.4rem;
}

.elapsed {
  font-weight: 700;
  font-size: 0.95rem;
}

.ticket-status {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  padding: 0.15rem 0.5rem;
  font-size: 0.72rem;
  text-transform: uppercase;
}

.line-list {
  list-style: none;
  margin: 0;
  padding: 0.15rem 0.35rem;
}

.line-row {
  padding: 0.1rem 0;
}

.line-btn {
  width: 100%;
  min-height: 40px;
  border: 1px solid transparent;
  border-radius: 0.65rem;
  background: transparent;
  color: inherit;
  text-align: left;
  padding: 0.4rem 0.55rem;
  font: inherit;
}

.line-row.selected .line-btn {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 16%, transparent);
}

.line-btn strong {
  display: block;
  font-size: 0.98rem;
}

.line-note {
  display: block;
  color: #fbbf24;
  margin-top: 0.1rem;
}

.line-addition {
  display: block;
  margin-top: 0.05rem;
}

.ticket-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.45rem;
  padding: 0.6rem;
  border-top: 1px solid var(--border);
}

.action-btn {
  min-width: 0;
  min-height: 44px;
  padding-left: 0.4rem;
  padding-right: 0.4rem;
  font-weight: 700;
  font-size: 0.92rem;
  white-space: normal;
  appearance: none;
  -webkit-appearance: none;
}

.partial-btn {
  background: var(--card);
  color: var(--text);
  border: 1px solid var(--border);
}

.complete-btn {
  background: var(--primary);
  color: white;
}
</style>
