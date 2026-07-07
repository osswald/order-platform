<template>
  <div>
    <h1>
      Kellner
      <span v-if="isTest" class="test-pill">TESTBETRIEB</span>
    </h1>
    <p class="muted">{{ event?.name }} · {{ waiter?.name }}</p>

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
      <button type="button" class="btn primary hub-btn" @click="router.push({ name: 'table-new' })">
        Neue Bestellung
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'table-settle-keypad' })">
        Tisch abrechnen
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'tables-open' })">
        Offene Tische
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'collective-open' })">
        Sammelrechnungen
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'stock' })">
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
        v-if="androidApp"
        type="button"
        class="btn hub-btn"
        @click="router.push({ name: 'android-printer' })"
      >
        Bluetooth Drucker
      </button>
    </div>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="switchWaiter">Kellner wechseln</button>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isAndroidApp } from '@/api'
import { useEventContext } from '@/composables/useEventContext'
import { maybeEndShiftOnSwitch } from '@/composables/useShiftSession'
import { useStationPrintFailures } from '@/composables/useStationPrintFailures'

const router = useRouter()
const { event, waiter, setWaiter, selectedEventId } = useEventContext()
const { failedCount, loadFailedJobs } = useStationPrintFailures()
const androidApp = computed(() => isAndroidApp())
const isTest = computed(() => String(event.value?.status ?? '').toLowerCase() === 'test')

onMounted(() => {
  const eventId = selectedEventId.value
  const waiterUuid = waiter.value?.uuid
  if (eventId && waiterUuid) {
    loadFailedJobs({ eventId, waiterUuid })
  }
})

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
.test-pill {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: #f59e0b;
  color: #1c1917;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  vertical-align: middle;
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
</style>
