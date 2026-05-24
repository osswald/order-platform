<template>
  <div>
    <h1>Events</h1>
    <p class="muted">Aktives Event wählen.</p>

    <p v-if="loading" class="muted">Bundle wird geladen…</p>

    <div v-else-if="!bundleReady" class="card">
      <p>Noch keine gültige Konfiguration auf diesem Gerät.</p>
      <p class="muted small">Über <strong>Admin</strong> unten die Konfiguration von der Cloud laden.</p>
    </div>

    <div v-else-if="!events.length" class="card">
      <p>
        Synchronisation war erfolgreich, aber die Cloud liefert <strong>0 aktive Events</strong> für dieses Gerät.
      </p>
      <p class="muted small">
        Prüfen Sie in der Cloud: Status <strong>Testbetrieb</strong> oder <strong>Produktivbetrieb</strong>,
        Start/Ende umfasst <strong>heute (UTC)</strong>, Server-Gerät mit Ausleihe für heute, Organisation passend.
      </p>
      <button type="button" class="btn" :disabled="loading" @click="reload">Erneut laden</button>
    </div>

    <ul v-else class="event-list">
      <li v-for="e in events" :key="e.id">
        <button type="button" class="event-btn" @click="pick(e)">
          <span class="event-name">{{ e.name }}</span>
          <span class="muted">{{ e.currency }} · {{ paymentModeLabel(e.payment_mode) }} · {{ eventStatusLabel(e.status) }}</span>
        </button>
      </li>
    </ul>

    <div class="admin-block card">
      <button type="button" class="btn hub-btn" @click="goAdmin">Admin</button>
      <p class="muted small">
        Konfiguration laden und Sync. Beim ersten Start ohne Code; nach Pi Admin-Code in der Cloud ist der
        6-stellige Code nötig.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminSession } from '../composables/useAdminSession'
import { useBundle } from '../composables/useBundle'
import { useWaiterSession } from '../composables/useWaiterSession'
import { setRegisterSession } from '../store'
import { eventStatusLabel } from '../utils/eventStatus'

const router = useRouter()
const loading = ref(false)
const { bundle, isBundleReady, refreshBundle, showToast, selectedEventId } = useBundle()
const { setWaiter } = useWaiterSession()
const { adminUnlocked, requiresPin, setAdminUnlocked } = useAdminSession()

const events = computed(() => bundle.value?.events || [])
const bundleReady = isBundleReady

const PAYMENT_MODE_LABELS = {
  instant: 'Sofort bezahlt',
  pay_now: 'Jetzt bezahlen',
  pay_later: 'Später bezahlen',
}

function paymentModeLabel(mode) {
  return PAYMENT_MODE_LABELS[String(mode || '').toLowerCase()] || mode || '—'
}

async function reload() {
  loading.value = true
  try {
    const n = await refreshBundle()
    if (n > 0) showToast(`${n} Event(s) geladen.`, 'ok')
    else showToast('Weiterhin keine aktiven Events.', 'err')
  } catch (e) {
    showToast(e.message || 'Laden fehlgeschlagen', 'err')
  } finally {
    loading.value = false
  }
}

function pick(e) {
  selectedEventId.value = e.id
  setWaiter(null)
  setRegisterSession(null)
  router.push({ name: 'event-mode' })
}

function goAdmin() {
  if (!requiresPin.value || adminUnlocked.value) {
    if (!requiresPin.value) setAdminUnlocked(true)
    router.push({ name: 'admin' })
  } else {
    router.push({ name: 'admin-unlock', query: { redirect: '/admin' } })
  }
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.admin-block {
  margin-top: 1.25rem;
}
.admin-block .hub-btn {
  width: 100%;
  min-height: 48px;
  margin-bottom: 0.5rem;
}
.small {
  font-size: 0.8rem;
  line-height: 1.4;
}
.event-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.event-list li {
  margin-bottom: 0.5rem;
}
.event-btn {
  width: 100%;
  text-align: left;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  min-height: 52px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.event-name {
  font-weight: 600;
}
</style>
