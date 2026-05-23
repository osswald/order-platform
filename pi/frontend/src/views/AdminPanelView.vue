<template>
  <div>
    <h1>Admin</h1>
    <p class="muted">Konfiguration, Sync und Cloud-Push.</p>

    <div class="card">
      <div class="field">
        <label for="base">Pi-API Basis-URL</label>
        <input id="base" v-model="baseInput" class="input" type="url" placeholder="http://192.168.1.10:8001" />
        <p class="muted">Wird in diesem Browser gespeichert. Leer = Build-Default (<code>VITE_API_BASE</code>).</p>
      </div>
      <div class="row">
        <button type="button" class="btn" :disabled="busy" @click="saveBase">URL speichern</button>
        <button type="button" class="btn primary" :disabled="busy" @click="doPull">Konfiguration laden</button>
      </div>
      <p v-if="lastSyncAt" class="muted">Letzte Synchronisation: {{ lastSyncAt }}</p>
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
      <p v-if="syncError" class="muted" style="color: var(--danger)">{{ syncError }}</p>
    </div>

    <div v-if="bundle && eventCount" class="card">
      <p>{{ eventCount }} Event(s) im Bundle.</p>
      <button type="button" class="btn" @click="goEvents">Zu Events</button>
    </div>

    <div v-if="androidApp" class="card" style="margin-top: 1rem">
      <p>Android-App: Bluetooth-Drucker für Kellner-Belege konfigurieren.</p>
      <button type="button" class="btn" @click="router.push({ name: 'android-printer' })">Bluetooth Drucker</button>
    </div>

    <div class="card" style="margin-top: 1rem">
      <button type="button" class="btn" :disabled="pushing" @click="doPush">Ausstehende an Cloud senden</button>
      <p v-if="pushMsg" :class="pushOk ? 'ok' : 'err'" style="margin-top: 0.5rem">{{ pushMsg }}</p>
    </div>

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="endAdmin">Admin beenden</button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as store from '../store'
import { api, getApiBase, isAndroidApp, setApiBase } from '../api'

const router = useRouter()
const baseInput = ref('')
const busy = computed(() => store.busy.value)
const bundle = computed(() => store.bundle.value)
const lastSyncAt = computed(() => store.lastSyncAt.value)
const syncError = computed(() => store.syncError.value)
const eventCount = computed(() => store.bundle.value?.events?.length || 0)
const pushing = ref(false)
const pushMsg = ref('')
const pushOk = ref(true)
const syncStatus = ref(null)
const androidApp = computed(() => isAndroidApp())

function formatCycle(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

async function loadSyncStatus() {
  try {
    syncStatus.value = await api('/v1/sync/status')
  } catch {
    syncStatus.value = null
  }
}

onMounted(async () => {
  baseInput.value = getApiBase()
  try {
    await store.refreshBundle()
    await loadSyncStatus()
  } catch {
    /* Pi unreachable */
  }
})

function saveBase() {
  const v = baseInput.value.trim()
  if (v) setApiBase(v)
  else {
    localStorage.removeItem('pi_api_base')
    baseInput.value = getApiBase()
  }
  store.showToast('API-Basis gespeichert.', 'ok')
}

async function doPull() {
  store.busy.value = true
  store.syncError.value = ''
  try {
    const pull = await api('/v1/sync/pull', { method: 'POST' })
    const count = await store.refreshBundle()
    const n = pull?.event_count ?? count
    store.showToast(
      n > 0 ? `Konfiguration geladen (${n} Event(s)).` : 'Sync OK, aber keine aktiven Events in der Cloud.',
      n > 0 ? 'ok' : 'err',
    )
    await loadSyncStatus()
  } catch (e) {
    store.syncError.value = e.message || 'Laden fehlgeschlagen'
    store.showToast(store.syncError.value, 'err')
  } finally {
    store.busy.value = false
  }
}

async function doPush() {
  pushing.value = true
  pushMsg.value = ''
  try {
    const r = await api('/v1/sync/push', { method: 'POST' })
    pushMsg.value = `Gesendet: ${r.sent}${r.errors?.length ? `, Fehler: ${r.errors.length}` : ''}`
    pushOk.value = !r.errors?.length
    store.showToast(pushOk.value ? 'Push OK' : 'Push mit Fehlern', pushOk.value ? 'ok' : 'err')
    await loadSyncStatus()
  } catch (e) {
    pushMsg.value = e.message || 'Push fehlgeschlagen'
    pushOk.value = false
    store.showToast(pushMsg.value, 'err')
  } finally {
    pushing.value = false
  }
}

function goEvents() {
  router.push({ name: 'events' })
}

function endAdmin() {
  store.clearAdminSession()
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
</style>
