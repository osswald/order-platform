<template>
  <div>
    <h1>Kellner</h1>
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

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isAndroidApp } from '../api'
import { useEventContext } from '../composables/useEventContext'
import { maybeEndShiftOnSwitch } from '../composables/useShiftSession'
import { useStationPrintFailures } from '../composables/useStationPrintFailures'

const router = useRouter()
const { event, waiter, setWaiter, selectedEventId } = useEventContext()
const { failedCount, loadFailedJobs } = useStationPrintFailures()
const androidApp = computed(() => isAndroidApp())

onMounted(() => {
  loadFailedJobs({
    eventId: selectedEventId.value,
    waiterUuid: waiter.value?.uuid,
  })
})

async function switchWaiter() {
  const ok = await maybeEndShiftOnSwitch({
    event: event.value,
    eventId: event.value?.id,
    subjectType: 'waiter',
    waiterUuid: waiter.value?.uuid,
  })
  if (!ok) return
  setWaiter(null)
  router.push({ name: 'login' })
}
</script>

<style scoped>
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
