<template>
  <div>
    <h1>Synchronisation</h1>
    <p class="muted">Konfiguration laden und Änderungen an die Cloud senden.</p>

    <div class="card">
      <h2 class="card-title">Pi-API Basis-URL</h2>
      <p class="muted small">Adresse des Pi-Backends (ohne Pfad). Nach Änderung Verbindung testen.</p>
      <label>
        URL
        <input v-model="apiBaseInput" type="url" autocomplete="off" placeholder="http://192.168.192.10" />
      </label>
      <div class="row actions">
        <button type="button" class="btn" :disabled="apiBusy" @click="testApiBase">Verbindung testen</button>
        <button type="button" class="btn primary" :disabled="apiBusy || !apiTestedOk" @click="saveApiBaseUrl">
          Speichern
        </button>
      </div>
      <p v-if="apiMessage" :class="apiMessageOk ? 'ok' : 'err'">{{ apiMessage }}</p>
    </div>

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
          <template v-if="syncStatus.last_cycle_at"> · Zyklus {{ formatCycle(String(syncStatus.last_cycle_at)) }}</template>
        </template>
        <template v-else> · Cloud nicht konfiguriert</template>
      </p>
      <p v-if="syncStatus?.configured" class="muted small">
        Auto-Sync aktiv bedeutet: Der Pi synchronisiert automatisch im Hintergrund. Ausstehend zeigt die Anzahl lokaler
        Änderungen, die noch nicht in die Cloud übertragen wurden.
      </p>
      <p v-if="syncError" class="muted err">{{ syncError }}</p>
    </div>

    <div class="card">
      <button type="button" class="btn" :disabled="pushing" @click="doPush">Ausstehende an Cloud senden</button>
      <p v-if="pushMsg" :class="pushOk ? 'ok' : 'err'" style="margin-top: 0.5rem">{{ pushMsg }}</p>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getApiBase } from '@/api'
import { useSyncOperations } from '@/composables/useSyncOperations'
import { useBundle } from '@/composables/useBundle'
import { formatDateTime, parseApiDate } from '@/utils/dateFormat'
import { getErrorMessage } from '@/types/api'
import { probeApiBase } from '@/utils/probeApiBase'

const router = useRouter()
const { syncStatus, loadSyncStatus, pullConfiguration, pushOutbox, saveApiBase } = useSyncOperations()
const { busy, lastSyncAt, syncError, showToast } = useBundle()
const pushing = ref(false)
const pushMsg = ref('')
const pushOk = ref(true)
const apiBaseInput = ref('')
const apiBusy = ref(false)
const apiTestedOk = ref(false)
const apiMessage = ref('')
const apiMessageOk = ref(true)

const formatCycle = formatDateTime

const lastSyncDisplay = computed(() => {
  if (!lastSyncAt.value) return '—'
  return `${formatDateTime(lastSyncAt.value)} (${relativeFromNow(lastSyncAt.value)})`
})

function relativeFromNow(iso: string | null | undefined) {
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

onMounted(async () => {
  apiBaseInput.value = getApiBase()
  try {
    await loadSyncStatus()
  } catch {
    /* Pi unreachable */
  }
})

async function testApiBase() {
  apiBusy.value = true
  apiMessage.value = ''
  apiTestedOk.value = false
  try {
    const result = await probeApiBase(apiBaseInput.value)
    if (result.reachable) {
      apiTestedOk.value = true
      apiMessage.value = 'Verbindung OK.'
      apiMessageOk.value = true
    } else {
      apiMessage.value =
        result.reason === 'network' ? 'Pi nicht erreichbar.' : result.message || 'Verbindung fehlgeschlagen.'
      apiMessageOk.value = false
    }
  } finally {
    apiBusy.value = false
  }
}

function saveApiBaseUrl() {
  if (!apiTestedOk.value) return
  saveApiBase(apiBaseInput.value.trim())
  apiMessage.value = `Gespeichert: ${getApiBase()}`
  apiMessageOk.value = true
}

async function doPull() {
  try {
    await pullConfiguration()
  } catch {
    /* toast shown in composable */
  }
}

async function doPush() {
  pushing.value = true
  pushMsg.value = ''
  try {
    const result = (await pushOutbox()) as { sent?: number; errors?: unknown[] }
    pushMsg.value = `Gesendet: ${result.sent ?? 0}${result.errors?.length ? `, Fehler: ${result.errors.length}` : ''}`
    pushOk.value = !result.errors?.length
  } catch (error: unknown) {
    pushMsg.value = getErrorMessage(error, 'Push fehlgeschlagen')
    pushOk.value = false
    showToast(pushMsg.value, 'err')
  } finally {
    pushing.value = false
  }
}

function goBack() {
  router.push({ name: 'admin' })
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
.card-title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}
label {
  display: block;
  margin-top: 0.5rem;
}
label input {
  width: 100%;
  margin-top: 0.35rem;
}
</style>
