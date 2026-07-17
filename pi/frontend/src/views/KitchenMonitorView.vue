<template>
  <div class="kitchen-monitor">
    <section v-if="!kitchenPrinters.length" class="card">
      <p>Für dieses Event ist kein Küchenmonitor aktiv.</p>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </section>

    <section v-else-if="unknownPrinterSlug" class="card">
      <p>Unbekannte Küchenmonitor-Station.</p>
      <p class="muted">URL-Segment: {{ printerSlug }}</p>
    </section>

    <template v-else>
      <KitchenMonitorHeader
        :station-label="selectedPrinter?.label || 'Küchenmonitor'"
        :event-name="event?.name || 'Event'"
        :view-mode="viewMode"
        :loading="loading"
        :show-additions="showAdditions"
        @set-view-mode="setViewMode"
        @set-show-additions="setShowAdditions"
        @refresh="loadOrders"
      />

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading && !orders.length" class="muted">Laden…</p>

      <div class="kitchen-body" :class="{ 'kitchen-body--products': viewMode === 'products' }">
        <KitchenOrderColumns
          v-if="viewMode === 'orders'"
          :orders="orders"
          :event="event"
          :busy-ticket-id="busyTicketId"
          :selected-qty="lineSelection.selectedQty"
          @cycle-line="lineSelection.cycleLine"
          @partial-print="onPartialPrint"
          @complete-print="onCompletePrint"
        />

        <KitchenProductList v-else :summary="productSummary" :show-additions="showAdditions" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import KitchenMonitorHeader from '@/components/kitchen/KitchenMonitorHeader.vue'
import KitchenOrderColumns from '@/components/kitchen/KitchenOrderColumns.vue'
import KitchenProductList from '@/components/kitchen/KitchenProductList.vue'
import { useEventContext } from '@/composables/useEventContext'
import { useKitchenLineSelection } from '@/composables/useKitchenLineSelection'
import { useKitchenMonitor } from '@/composables/useKitchenMonitor'
import type { KitchenOrderTicket } from '@/types/api'
import { buildKitchenProductSummary } from '@/utils/kitchenProductSummary'
import {
  kitchenViewModeFromSlug,
  kitchenViewSlugFromMode,
  type KitchenMonitorViewMode,
} from '@/utils/kitchenMonitorViewSlug'

const router = useRouter()
const route = useRoute()
const { event } = useEventContext()

const printerSlug = computed(() => String(route.params.printerSlug || ''))

const {
  kitchenPrinters,
  selectedPrinter,
  unknownPrinterSlug,
  orders,
  loading,
  error,
  busyTicketId,
  loadOrders,
  printComplete,
  printPartial,
  startPolling,
  stopPolling,
} = useKitchenMonitor({ event, printerSlug })

onMounted(() => {
  void loadOrders()
  startPolling()
  if (!viewModeMatchesRoute(viewMode.value)) {
    syncViewToRoute(viewMode.value)
  }
})

onUnmounted(() => {
  stopPolling()
})

const lineSelection = useKitchenLineSelection()

const viewMode = ref<KitchenMonitorViewMode>(resolveViewMode())
const showAdditions = ref(readShowAdditions())

function viewStorageKey() {
  return `pi_kitchen_view_${event.value?.id || 'none'}_${printerSlug.value || 'none'}`
}

function additionsStorageKey() {
  return `pi_kitchen_show_additions_${event.value?.id || 'none'}_${printerSlug.value || 'none'}`
}

function readViewModeFromStorage(): KitchenMonitorViewMode {
  try {
    const saved = localStorage.getItem(viewStorageKey())
    return saved === 'products' ? 'products' : 'orders'
  } catch {
    return 'orders'
  }
}

function resolveViewMode(): KitchenMonitorViewMode {
  const routeView = String(route.params.view || '')
  if (routeView) return kitchenViewModeFromSlug(routeView)
  return readViewModeFromStorage()
}

function readShowAdditions(): boolean {
  try {
    return localStorage.getItem(additionsStorageKey()) !== '0'
  } catch {
    return true
  }
}

function syncViewToRoute(mode: KitchenMonitorViewMode) {
  const nextView = kitchenViewSlugFromMode(mode)
  if (String(route.params.view || '') === nextView) return
  if (!route.params.view && mode === 'orders') return
  void router.replace({
    name: 'kitchen',
    params: {
      printerSlug: printerSlug.value,
      view: nextView,
    },
  })
}

function viewModeMatchesRoute(mode: KitchenMonitorViewMode): boolean {
  const slug = String(route.params.view || '')
  if (!slug) return mode === 'orders'
  return kitchenViewModeFromSlug(slug) === mode
}

function setViewMode(mode: KitchenMonitorViewMode) {
  viewMode.value = mode
  try {
    localStorage.setItem(viewStorageKey(), mode)
  } catch {
    /* ignore */
  }
  syncViewToRoute(mode)
}

function setShowAdditions(value: boolean) {
  showAdditions.value = value
  try {
    localStorage.setItem(additionsStorageKey(), value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

watch(
  () => [route.params.view, event.value?.id, printerSlug.value] as const,
  () => {
    viewMode.value = resolveViewMode()
    showAdditions.value = readShowAdditions()
  },
)

const productSummary = computed(() => buildKitchenProductSummary(orders.value, event.value))

watch(
  orders,
  (rows) => {
    const allLines = rows.flatMap((ticket) => ticket.lines || [])
    lineSelection.reconcileLines(allLines)
  },
  { deep: true },
)

async function onPartialPrint(ticket: KitchenOrderTicket) {
  const payload = lineSelection.payloadForTicket(ticket)
  await printPartial(ticket, payload)
  lineSelection.clearTicket(ticket)
}

async function onCompletePrint(ticket: KitchenOrderTicket) {
  await printComplete(ticket)
  lineSelection.clearTicket(ticket)
}
</script>

<style scoped>
.kitchen-monitor {
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  height: 100dvh;
  padding: 0.25rem;
  overflow: hidden;
}

.kitchen-body {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.kitchen-body--products {
  overflow-x: hidden;
  overflow-y: auto;
}
</style>
