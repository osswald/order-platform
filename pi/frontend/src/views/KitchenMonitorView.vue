<template>
  <div class="kitchen-monitor">
    <header class="kitchen-header">
      <div>
        <h1>Kitchen Monitor</h1>
        <p class="muted">{{ event?.name || 'Event' }}</p>
      </div>
      <RouterLink class="btn small-btn" :to="{ name: waiter ? 'hub' : 'events' }">
        Zurück
      </RouterLink>
    </header>

    <section v-if="!kitchenStations.length" class="card">
      <p>Für dieses Event ist kein Kitchen Monitor aktiv.</p>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </section>

    <template v-else>
      <div v-if="kitchenStations.length > 1" class="station-tabs">
        <button
          v-for="st in kitchenStations"
          :key="st.uuid"
          type="button"
          class="station-tab"
          :class="{ active: st.uuid === selectedStationUuid }"
          @click="selectStation(st.uuid)"
        >
          {{ st.name }}
        </button>
      </div>

      <div class="toolbar">
        <div>
          <strong>{{ selectedStation?.name }}</strong>
          <span class="muted"> · {{ orders.length }} offen</span>
        </div>
        <button type="button" class="btn small-btn" :disabled="loading" @click="loadOrders">
          Aktualisieren
        </button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading && !orders.length" class="muted">Laden…</p>
      <p v-else-if="!orders.length" class="empty">Keine offenen Bestellungen.</p>

      <div class="ticket-grid">
        <article
          v-for="ticket in orders"
          :key="ticket.id"
          class="ticket-card"
          :class="{ busy: busyTicketId === ticket.id }"
          @click="printTicket(ticket)"
        >
          <div class="ticket-top">
            <div>
              <div class="ticket-title">
                Bestellung #{{ ticket.order_number || ticket.id }}
              </div>
              <div class="muted">
                <template v-if="ticket.pickup_code">Pickup {{ ticket.pickup_code }}</template>
                <template v-else>Tisch {{ ticket.table_number || '—' }}</template>
                <span v-if="ticket.waiter_name"> · {{ ticket.waiter_name }}</span>
              </div>
            </div>
            <span class="ticket-status">{{ ticket.status }}</span>
          </div>

          <ul class="line-list">
            <li v-for="line in ticket.lines" :key="line.id" class="line-row">
              <div class="line-main">
                <strong>{{ line.qty_remaining }}x {{ lineName(line.line) }}</strong>
                <span v-if="line.line.note" class="line-note">{{ line.line.note }}</span>
                <span v-if="additionText(line.line)" class="muted">{{ additionText(line.line) }}</span>
                <span v-if="line.qty_printed" class="muted">
                  {{ line.qty_printed }}/{{ line.qty_total }} gedruckt
                </span>
              </div>
              <button
                type="button"
                class="unit-btn"
                :disabled="busyLineId === line.id || busyTicketId === ticket.id"
                @click.stop="printLineUnit(ticket, line)"
              >
                1 fertig
              </button>
            </li>
          </ul>

          <p class="tap-hint">Antippen druckt alle übrigen Einheiten sofort.</p>
        </article>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useEventContext } from '../composables/useEventContext'

const router = useRouter()
const { event, waiter } = useEventContext()
const kitchenStations = computed(() =>
  (event.value?.configuration?.stations || [])
    .filter((st) => st.kitchen_monitor_enabled && st.uuid)
    .map((st) => ({
      uuid: String(st.uuid),
      name: st.name || `Station ${String(st.uuid).slice(0, 8)}`,
      sort_order: Number(st.sort_order) || 0,
    }))
    .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
)

const selectedStationUuid = ref('')
const orders = ref([])
const loading = ref(false)
const error = ref('')
const busyTicketId = ref(null)
const busyLineId = ref(null)
let pollTimer = null

const selectedStation = computed(() =>
  kitchenStations.value.find((st) => st.uuid === selectedStationUuid.value) || kitchenStations.value[0] || null,
)

function storageKey() {
  return `pi_kitchen_station_${event.value?.id || 'none'}`
}

function restoreStation() {
  const stations = kitchenStations.value
  if (!stations.length) {
    selectedStationUuid.value = ''
    return
  }
  let saved = ''
  try {
    saved = localStorage.getItem(storageKey()) || ''
  } catch {
    saved = ''
  }
  const match = stations.find((st) => st.uuid === saved)
  selectedStationUuid.value = (match || stations[0]).uuid
}

function selectStation(uuid) {
  selectedStationUuid.value = uuid
  try {
    localStorage.setItem(storageKey(), uuid)
  } catch {
    /* ignore private mode */
  }
  loadOrders()
}

function lineName(line) {
  if (line?.article_name) return line.article_name
  const aid = line?.article_id
  const article = event.value?.articles?.[String(aid)] || event.value?.articles?.[aid]
  return article?.name || `#${aid}`
}

function additionText(line) {
  const additions = line?.additions || []
  if (!additions.length) return ''
  return additions
    .map((add) => {
      const id = Number(add.article_id)
      const article = event.value?.articles?.[String(id)] || event.value?.articles?.[id]
      const name = add.name || article?.name || `#${id}`
      return `+ ${Math.max(1, Number(add.qty) || 1)}x ${name}`
    })
    .join(', ')
}

async function loadOrders() {
  const ev = event.value
  const stationUuid = selectedStationUuid.value
  if (!ev?.id || !stationUuid) {
    orders.value = []
    return
  }
  loading.value = true
  error.value = ''
  try {
    const data = await api(`/v1/kitchen/orders?event_id=${encodeURIComponent(ev.id)}&station_uuid=${encodeURIComponent(stationUuid)}`)
    orders.value = data?.orders || []
  } catch (e) {
    error.value = e.message || 'Kitchen Monitor konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function printTicket(ticket) {
  if (busyTicketId.value || busyLineId.value) return
  busyTicketId.value = ticket.id
  error.value = ''
  try {
    await api(`/v1/kitchen/tickets/${ticket.id}/print`, { method: 'POST' })
    await loadOrders()
  } catch (e) {
    error.value = e.message || 'Drucken fehlgeschlagen.'
  } finally {
    busyTicketId.value = null
  }
}

async function printLineUnit(ticket, line) {
  if (busyTicketId.value || busyLineId.value) return
  busyLineId.value = line.id
  error.value = ''
  try {
    await api(`/v1/kitchen/tickets/${ticket.id}/lines/${line.id}/print-one`, { method: 'POST' })
    await loadOrders()
  } catch (e) {
    error.value = e.message || 'Drucken fehlgeschlagen.'
  } finally {
    busyLineId.value = null
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible' && !busyTicketId.value && !busyLineId.value) {
      loadOrders()
    }
  }, 5000)
}

watch(kitchenStations, restoreStation, { immediate: true })
watch(selectedStationUuid, () => {
  loadOrders()
})

onMounted(() => {
  loadOrders()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.kitchen-monitor {
  min-height: 100vh;
  padding: 0.75rem 1rem 1rem;
}

.kitchen-header,
.toolbar,
.ticket-top,
.line-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.kitchen-header {
  margin-bottom: 1rem;
}

.kitchen-header h1 {
  margin-bottom: 0.15rem;
}

.small-btn {
  min-height: 38px;
  padding: 0.45rem 0.75rem;
}

.station-tabs {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
  margin-bottom: 0.75rem;
}

.station-tab {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--card);
  color: var(--text);
  padding: 0.65rem 1rem;
  font: inherit;
  white-space: nowrap;
}

.station-tab.active {
  border-color: var(--primary);
  background: var(--primary);
  color: white;
}

.toolbar {
  margin-bottom: 0.75rem;
}

.empty {
  text-align: center;
  color: var(--muted);
  margin-top: 3rem;
  font-size: 1.2rem;
}

.ticket-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 280px));
  justify-content: start;
  gap: 0.85rem;
}

.ticket-card {
  border: 1px solid var(--border);
  border-radius: 1rem;
  background: var(--card);
  padding: 1rem;
  cursor: pointer;
  transition: transform 0.12s ease, opacity 0.12s ease;
}

.ticket-card:active {
  transform: scale(0.99);
}

.ticket-card.busy {
  opacity: 0.65;
  pointer-events: none;
}

.ticket-title {
  font-size: 1.25rem;
  font-weight: 800;
}

.ticket-status {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  padding: 0.25rem 0.55rem;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.line-list {
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
}

.line-row {
  align-items: flex-start;
  padding: 0.75rem 0;
  border-top: 1px solid var(--border);
}

.line-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.line-note {
  color: #fbbf24;
}

.unit-btn {
  border: none;
  border-radius: 0.75rem;
  background: var(--primary);
  color: white;
  padding: 0.65rem 0.75rem;
  font: inherit;
  font-weight: 700;
  white-space: nowrap;
}

.unit-btn:disabled {
  opacity: 0.6;
}

.tap-hint {
  margin: 0.75rem 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}
</style>
