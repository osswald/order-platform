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
import { getApiBase, isAndroidApp } from '../api'
import { useAdminSession } from '../composables/useAdminSession'
import { useBundle } from '../composables/useBundle'
import { useSyncOperations } from '../composables/useSyncOperations'
import { formatDateTime } from '../utils/dateFormat'

const router = useRouter()
const { clearAdminSession } = useAdminSession()
const { syncStatus, loadSyncStatus, saveApiBase, pullConfiguration, pushOutbox } = useSyncOperations()
const { bundle, busy, lastSyncAt, syncError, refreshBundle, showToast } = useBundle()
const baseInput = ref('')
const eventCount = computed(() => bundle.value?.events?.length || 0)
const pushing = ref(false)
const pushMsg = ref('')
const pushOk = ref(true)
const androidApp = computed(() => isAndroidApp())

const formatCycle = formatDateTime

onMounted(async () => {
  baseInput.value = getApiBase()
  try {
    await refreshBundle()
    await loadSyncStatus()
  } catch {
    /* Pi unreachable */
  }
})

function saveBase() {
  baseInput.value = saveApiBase(baseInput.value)
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
</style>
