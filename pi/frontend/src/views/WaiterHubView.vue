<template>
  <div>
    <h1>
      Kellner
      <TestBetriebPill v-if="isTest" />
    </h1>
    <p class="muted">
      {{ event?.name }} · {{ waiter?.name
      }}<template v-if="sumupDeviceLabel"> · SumUp: {{ sumupDeviceLabel }}</template>
    </p>

    <PiUnreachableBanner />

    <div v-if="failedCount > 0" class="card print-fail-banner">
      <p>
        <strong>{{ failedCount }} Druckfehler</strong>
        — Stationsbons konnten nicht gedruckt werden.
      </p>
      <button type="button" class="btn primary" @click="router.push({ name: 'print-failures' })">
        Anzeigen & erneut drucken
      </button>
    </div>

    <div class="hub-actions">
      <button
        type="button"
        class="btn primary hub-btn"
        :disabled="gating"
        @click="goGated({ name: 'table-new' })"
      >
        {{ gating ? 'Prüfe Verbindung…' : 'Neue Bestellung' }}
      </button>
      <button
        type="button"
        class="btn hub-btn"
        :disabled="gating"
        @click="goGated({ name: 'table-settle-keypad' })"
      >
        Tisch abrechnen
      </button>
      <button
        type="button"
        class="btn hub-btn"
        :disabled="gating"
        @click="goGated({ name: 'tables-open' })"
      >
        Offene Tische
      </button>
      <button
        type="button"
        class="btn hub-btn"
        :disabled="gating"
        @click="goGated({ name: 'collective-open' })"
      >
        Sammelrechnungen
      </button>
      <button
        type="button"
        class="btn hub-btn"
        :disabled="gating"
        @click="goGated({ name: 'stock' })"
      >
        Lagerbestand
      </button>
      <button
        v-if="androidApp"
        type="button"
        class="btn hub-btn"
        @click="router.push({ name: 'receipts' })"
      >
        Belege / Nachdruck
      </button>
      <button
        v-if="androidApp && bluetoothPrinting"
        type="button"
        class="btn hub-btn"
        @click="router.push({ name: 'android-printer' })"
      >
        Bluetooth Drucker
      </button>
    </div>

    <div v-if="canSwitchSumupDevice" class="sumup-switch card">
      <button
        type="button"
        class="btn hub-btn sumup-switch-btn"
        :aria-expanded="readerListOpen"
        @click="toggleReaderList"
      >
        SumUp-Gerät wechseln
      </button>
      <ul v-if="readerListOpen" class="waiter-list">
        <li v-for="reader in sumupReaders" :key="reader.sumup_reader_id">
          <button
            type="button"
            class="waiter-row"
            :class="{ 'waiter-row--selected': reader.sumup_reader_id === waiter?.sumupReaderId }"
            @click="pickSumupReader(reader)"
          >
            <span class="waiter-row-name">{{ reader.label }}</span>
            <span
              v-if="reader.sumup_reader_id === waiter?.sumupReaderId"
              class="waiter-row-check"
              aria-hidden="true"
              >✓</span
            >
          </button>
        </li>
      </ul>
    </div>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="switchWaiter">Kellner wechseln</button>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import { isAndroidApp } from '@/api'
import PiUnreachableBanner from '@/components/PiUnreachableBanner.vue'
import TestBetriebPill from '@/components/TestBetriebPill.vue'
import { useEventContext } from '@/composables/useEventContext'
import { usePiConnectivity } from '@/composables/usePiConnectivity'
import { maybeEndShiftOnSwitch } from '@/composables/useShiftSession'
import { useStationPrintFailures } from '@/composables/useStationPrintFailures'
import { bundle } from '@/store'
import { isEventTest } from '@/utils/eventStatus'
import { bluetoothPrintingEnabled } from '@/utils/paymentReceiptPrompt'
import { eventPaymentTypes } from '@/utils/paymentTypes'
import {
  findSumupReaderLabel,
  getBundleSumupReaders,
  type SumupBundleReader,
} from '@/utils/sumupReaders'

const router = useRouter()
const { event, waiter, setWaiter, selectedEventId } = useEventContext()
const { failedCount, loadFailedJobs } = useStationPrintFailures()
const { ensureReachable } = usePiConnectivity()
const androidApp = computed(() => isAndroidApp())
const bluetoothPrinting = computed(() => bluetoothPrintingEnabled(event.value))
const isTest = computed(() => isEventTest(event.value?.status as string | undefined))
const gating = ref(false)
const readerListOpen = ref(false)

const sumupReaders = computed(() => getBundleSumupReaders(bundle.value))
const allowsSumupConnected = computed(() =>
  eventPaymentTypes(event.value).includes('sumup_connected'),
)
const sumupDeviceLabel = computed(() => {
  if (!allowsSumupConnected.value) return null
  const id = waiter.value?.sumupReaderId?.trim()
  if (!id) return null
  return findSumupReaderLabel(sumupReaders.value, id) || waiter.value?.sumupReaderLabel || null
})
const canSwitchSumupDevice = computed(
  () => allowsSumupConnected.value && sumupReaders.value.length > 1,
)

async function goGated(to: RouteLocationRaw) {
  if (gating.value) return
  gating.value = true
  try {
    const ok = await ensureReachable()
    if (!ok) return
    await router.push(to)
  } finally {
    gating.value = false
  }
}

onMounted(() => {
  const eventId = selectedEventId.value
  const waiterUuid = waiter.value?.uuid
  if (eventId && waiterUuid) {
    loadFailedJobs({ eventId, waiterUuid })
  }
})

function toggleReaderList() {
  readerListOpen.value = !readerListOpen.value
}

function pickSumupReader(reader: SumupBundleReader) {
  const w = waiter.value
  if (!w) return
  setWaiter({
    uuid: w.uuid,
    name: w.name,
    sumupReaderId: reader.sumup_reader_id,
    sumupReaderLabel: reader.label,
  })
  readerListOpen.value = false
}

async function switchWaiter() {
  const ev = event.value
  const waiterUuid = waiter.value?.uuid
  if (!ev?.id || !waiterUuid) return
  const ok = await maybeEndShiftOnSwitch({
    event: ev,
    eventId: ev.id,
    subjectType: 'waiter',
    waiterUuid,
  })
  if (!ok) return
  setWaiter(null)
  router.push({ name: 'login' })
}
</script>

<style scoped>
h1 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.print-fail-banner {
  margin-top: 1rem;
  padding: 1rem;
  border-color: var(--err, #c62828);
  background: color-mix(in srgb, var(--err, #c62828) 8%, var(--card));
}
.print-fail-banner p {
  margin: 0 0 0.75rem;
}
.hub-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}
.hub-btn {
  width: 100%;
  min-height: 56px;
  font-size: 1.1rem;
}
.sumup-switch {
  margin-top: 1rem;
  padding: 0.75rem;
}
.sumup-switch-btn {
  margin: 0;
}
.waiter-list {
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
}
.waiter-list li {
  margin-bottom: 0.5rem;
}
.waiter-list li:last-child {
  margin-bottom: 0;
}
.waiter-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--bg, var(--card));
  color: var(--text);
  cursor: pointer;
  min-height: 52px;
  text-align: left;
}
.waiter-row--selected {
  border-color: var(--accent, #ea580c);
  background: var(--card);
}
.waiter-row-name {
  font-weight: 600;
  font-size: 1.05rem;
}
.waiter-row-check {
  color: var(--accent, #ea580c);
  font-weight: 700;
}
</style>
