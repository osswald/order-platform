<template>
  <div>
    <h1>Admin</h1>
    <p class="muted">Konfiguration, Sync und Cloud-Push.</p>

    <div class="card">
      <div class="row">
        <button type="button" class="btn primary" :disabled="busy" @click="doPull">Konfiguration laden</button>
      </div>
      <p v-if="lastSyncAt" class="muted">Letzte Synchronisation: {{ lastSyncDisplay }}</p>
      <p v-else class="muted">Noch keine Synchronisation.</p>
      <p v-if="syncStatus" class="muted small">
        Auto-Sync:
        {{ syncStatus.auto_sync_enabled ? 'aktiv' : 'aus' }}
        <template v-if="syncStatus.configured">
          · ausstehend {{ syncStatus.pending_outbox_count }}
          <template v-if="syncStatus.last_cycle_at"> · Zyklus {{ formatCycle(syncStatus.last_cycle_at) }}</template>
        </template>
        <template v-else> · Cloud nicht konfiguriert</template>
      </p>
      <p v-if="syncStatus?.configured" class="muted small">
        Auto-Sync aktiv bedeutet: Der Pi synchronisiert automatisch im Hintergrund. Ausstehend zeigt die Anzahl lokaler
        Änderungen, die noch nicht in die Cloud übertragen wurden.
      </p>
      <p v-if="syncError" class="muted" style="color: var(--danger)">{{ syncError }}</p>
    </div>

    <div v-if="bundle && events.length" class="card">
      <h2>Betrieb</h2>
      <div class="field">
        <label for="ops-event">Event</label>
        <select id="ops-event" v-model="opsEventId" class="select">
          <option v-for="e in events" :key="e.id" :value="e.id">{{ e.name }}</option>
        </select>
      </div>

      <div v-if="opsEvent" class="ops-actions">
        <button
          type="button"
          class="btn hub-btn"
          :disabled="busy || testPrintBusy"
          @click="doTestPrint"
        >
          Testdruck
        </button>
        <p class="muted small test-print-hint">
          Druckt je Station einen Probebons — auch wenn dieselbe Drucker-IP mehrfach vorkommt.
        </p>
        <button
          v-if="hasKitchenMonitor"
          type="button"
          class="btn hub-btn"
          @click="openKitchen"
        >
          Küchenmonitor
        </button>
        <button
          v-if="hasCashRegisters"
          type="button"
          class="btn hub-btn"
          @click="openPickup"
        >
          Pickup Screen
        </button>
      </div>

      <div v-if="hasCashRegisters" class="display-section">
        <h3>Kundendisplay</h3>
        <div class="field">
          <label for="ops-register">Kasse</label>
          <select id="ops-register" v-model="opsRegisterUuid" class="select">
            <option v-for="reg in cashRegisters" :key="reg.uuid" :value="reg.uuid">{{ reg.name }}</option>
          </select>
        </div>
        <code v-if="displayUrl" class="display-url">{{ displayUrl }}</code>
        <div class="row">
          <button type="button" class="btn" :disabled="!displayUrl" @click="copyDisplayUrl">URL kopieren</button>
          <button type="button" class="btn" :disabled="!displayUrl" @click="openDisplay">Display öffnen</button>
        </div>
      </div>
    </div>

    <div v-if="bundle && eventCount" class="card">
      <p>{{ eventCount }} Event(s) im Bundle.</p>
      <button type="button" class="btn" @click="goEvents">Zu Events</button>
    </div>

    <div v-if="androidApp" class="card" style="margin-top: 1rem">
      <p>Android-App: Bluetooth-Drucker und Belegbreite (53/58/80 mm) für Kellner-Belege konfigurieren.</p>
      <button type="button" class="btn" @click="router.push({ name: 'android-printer' })">Bluetooth Drucker</button>
    </div>

    <div class="card" style="margin-top: 1rem">
      <button type="button" class="btn" :disabled="pushing" @click="doPush">Ausstehende an Cloud senden</button>
      <p v-if="pushMsg" :class="pushOk ? 'ok' : 'err'" style="margin-top: 0.5rem">{{ pushMsg }}</p>
    </div>

    <div v-if="setupStatus?.configured && setupStatus?.can_unpair" class="card" style="margin-top: 1rem">
      <h2>Gerät entkoppeln</h2>
      <p class="muted small">
        Entkoppeln sperrt die aktuelle SD-Karte in der Cloud und entfernt danach die lokale Kopplung.
      </p>
      <div class="field">
        <label for="unpair-secret">Werksschlüssel</label>
        <input
          id="unpair-secret"
          v-model="unpairSecret"
          class="input"
          type="password"
          autocomplete="off"
          placeholder="PI_SETUP_UNPAIR_SECRET"
        />
      </div>
      <button type="button" class="btn" :disabled="unpairLoading" @click="uncoupleDevice">
        {{ unpairLoading ? 'Entkopple...' : 'Gerät entkoppeln' }}
      </button>
      <p v-if="unpairMessage" :class="unpairOk ? 'ok' : 'err'" style="margin-top: 0.5rem">{{ unpairMessage }}</p>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="endAdmin">Admin beenden</button>

    <p class="muted small version-line">Vendiqo Pi {{ label }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, isAndroidApp } from '../api'
import { useAdminSession } from '../composables/useAdminSession'
import { useBundle } from '../composables/useBundle'
import { useSyncOperations } from '../composables/useSyncOperations'
import { formatDateTime, parseApiDate } from '../utils/dateFormat'
import { useAppVersion } from '../composables/useAppVersion'

const { label } = useAppVersion()

const router = useRouter()
const { clearAdminSession } = useAdminSession()
const { syncStatus, loadSyncStatus, pullConfiguration, pushOutbox } = useSyncOperations()
const { bundle, busy, lastSyncAt, syncError, refreshBundle, showToast, selectedEventId } = useBundle()
const opsEventId = ref(null)
const opsRegisterUuid = ref(null)
const eventCount = computed(() => bundle.value?.events?.length || 0)
const events = computed(() => bundle.value?.events || [])
const pushing = ref(false)
const pushMsg = ref('')
const pushOk = ref(true)
const setupStatus = ref(null)
const unpairSecret = ref('')
const unpairLoading = ref(false)
const unpairMessage = ref('')
const unpairOk = ref(true)
const testPrintBusy = ref(false)
const androidApp = computed(() => isAndroidApp())

const formatCycle = formatDateTime

const lastSyncDisplay = computed(() => {
  if (!lastSyncAt.value) return '—'
  return `${formatDateTime(lastSyncAt.value)} (${relativeFromNow(lastSyncAt.value)})`
})

const opsEvent = computed(() => events.value.find((e) => Number(e.id) === Number(opsEventId.value)) || null)

const cashRegisters = computed(() => {
  const regs = opsEvent.value?.configuration?.cash_registers || []
  return regs
    .slice()
    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'de'))
})

const hasKitchenMonitor = computed(() => Boolean(opsEvent.value?.kitchen_monitors_enabled))

const hasCashRegisters = computed(() => cashRegisters.value.length > 0)

const displayUrl = computed(() => {
  if (!opsRegisterUuid.value) return ''
  const path = router.resolve({
    name: 'register-display',
    params: { registerUuid: opsRegisterUuid.value },
  }).href
  if (typeof window === 'undefined') return path
  return `${window.location.origin}${path}`
})

function relativeFromNow(iso) {
  const ts = parseApiDate(iso)
  if (!ts) return 'unbekannt'
  const diffMs = Date.now() - ts.getTime()
  if (diffMs < 0) return 'gerade eben'
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < minute) return 'gerade eben'
  if (diffMs < hour) {
    const mins = Math.floor(diffMs / minute)
    return `vor ${mins} Min.`
  }
  if (diffMs < day) {
    const hours = Math.floor(diffMs / hour)
    return `vor ${hours} Std.`
  }
  const days = Math.floor(diffMs / day)
  return `vor ${days} Tag${days === 1 ? '' : 'en'}`
}

watch(events, (list) => {
  if (!list.length) {
    opsEventId.value = null
    opsRegisterUuid.value = null
    return
  }
  if (opsEventId.value == null || !list.some((e) => Number(e.id) === Number(opsEventId.value))) {
    opsEventId.value = selectedEventId.value ?? list[0].id
  }
}, { immediate: true })

watch(cashRegisters, (regs) => {
  if (!regs.length) {
    opsRegisterUuid.value = null
    return
  }
  if (opsRegisterUuid.value == null || !regs.some((r) => r.uuid === opsRegisterUuid.value)) {
    opsRegisterUuid.value = regs[0].uuid
  }
}, { immediate: true })

onMounted(async () => {
  try {
    setupStatus.value = await api('/v1/setup/status')
    await refreshBundle()
    await loadSyncStatus()
  } catch {
    /* Pi unreachable */
  }
})

async function doPull() {
  try {
    await pullConfiguration()
  } catch {
    /* toast shown in composable */
  }
}

async function doTestPrint() {
  if (opsEventId.value == null) return
  testPrintBusy.value = true
  try {
    const data = await api('/v1/printers/test-station-prints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_id: opsEventId.value }),
    })
    const printed = data.printed ?? 0
    const failed = data.failed ?? 0
    const total = (data.results || []).length
    if (failed === 0) {
      showToast(`Testdruck: ${printed}/${total} Stationen OK.`, 'ok')
    } else {
      const firstErr = (data.results || []).find((r) => !r.ok)?.error
      showToast(
        `Testdruck: ${printed}/${total} OK, ${failed} Fehler.${firstErr ? ` ${firstErr}` : ''}`,
        'err',
      )
    }
  } catch (error) {
    showToast(error.message || 'Testdruck fehlgeschlagen.', 'err')
  } finally {
    testPrintBusy.value = false
  }
}

async function doPush() {
  pushing.value = true
  pushMsg.value = ''
  try {
    const result = await pushOutbox()
    pushMsg.value = `Gesendet: ${result.sent}${result.errors?.length ? `, Fehler: ${result.errors.length}` : ''}`
    pushOk.value = !result.errors?.length
  } catch (error) {
    pushMsg.value = error.message || 'Push fehlgeschlagen'
    pushOk.value = false
    showToast(pushMsg.value, 'err')
  } finally {
    pushing.value = false
  }
}

async function uncoupleDevice() {
  if (!setupStatus.value?.configured || !setupStatus.value?.can_unpair) return
  if (!unpairSecret.value.trim()) {
    unpairMessage.value = 'Werksschlüssel erforderlich.'
    unpairOk.value = false
    return
  }
  const confirmed = window.confirm(
    'Gerät wirklich entkoppeln? Die aktuelle SD-Karte wird in der Cloud gesperrt und lokal entkoppelt.',
  )
  if (!confirmed) return
  unpairLoading.value = true
  unpairMessage.value = ''
  try {
    setupStatus.value = await api('/v1/setup/unpair', {
      method: 'POST',
      body: JSON.stringify({ unpair_secret: unpairSecret.value }),
    })
    unpairSecret.value = ''
    unpairOk.value = true
    unpairMessage.value = 'Gerät erfolgreich entkoppelt.'
    clearAdminSession()
    window.setTimeout(() => router.replace({ name: 'setup' }), 600)
  } catch (error) {
    unpairOk.value = false
    unpairMessage.value = error.message || 'Entkoppeln fehlgeschlagen.'
  } finally {
    unpairLoading.value = false
  }
}

function openKitchen() {
  selectedEventId.value = opsEventId.value
  router.push({ name: 'kitchen' })
}

function openPickup() {
  selectedEventId.value = opsEventId.value
  router.push({ name: 'pickup' })
}

async function copyDisplayUrl() {
  const url = displayUrl.value
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    showToast('URL kopiert.', 'ok')
  } catch {
    showToast(url, 'ok')
  }
}

function openDisplay() {
  const url = displayUrl.value
  if (!url) return
  selectedEventId.value = opsEventId.value
  window.open(url, '_blank', 'noopener,noreferrer')
}

function goEvents() {
  router.push({ name: 'events' })
}

function endAdmin() {
  clearAdminSession()
  router.replace({ name: 'events' })
}
</script>

<style scoped>
.small {
  font-size: 0.8rem;
}
.ok {
  color: var(--ok);
}
.err {
  color: var(--danger);
}
.ops-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.test-print-hint {
  margin: 0;
}
.hub-btn {
  width: 100%;
}
.display-section h3 {
  font-size: 1rem;
  margin: 0 0 0.75rem;
}
.display-url {
  display: block;
  word-break: break-all;
  font-size: 0.8rem;
  margin-bottom: 0.75rem;
}
.version-line {
  margin: 1.5rem 0 0;
  text-align: center;
}
</style>
