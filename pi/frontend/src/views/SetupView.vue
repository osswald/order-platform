<template>
  <div>
    <h1>Sync</h1>
    <p class="muted">Konfiguration von der Cloud laden (Pi muss erreichbar sein).</p>

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
      <p v-if="syncError" class="muted" style="color: var(--danger)">{{ syncError }}</p>
    </div>

    <div v-if="bundle && eventCount" class="card">
      <p>{{ eventCount }} Event(s) im Bundle.</p>
      <button type="button" class="btn primary" @click="goEvents">Weiter zu Events</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as store from '../store'
import { api, getApiBase, setApiBase } from '../api'

const router = useRouter()
const route = useRoute()
const baseInput = ref('')
const busy = computed(() => store.busy.value)
const bundle = computed(() => store.bundle.value)
const lastSyncAt = computed(() => store.lastSyncAt.value)
const syncError = computed(() => store.syncError.value)
const eventCount = computed(() => store.bundle.value?.events?.length || 0)

onMounted(async () => {
  baseInput.value = getApiBase()
  try {
    await store.refreshBundle()
  } catch {
    /* Pi unreachable — user can sync manually */
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
    const redir = route.query.redirect
    if (typeof redir === 'string' && redir.startsWith('/')) {
      router.replace(redir)
    }
  } catch (e) {
    store.syncError.value = e.message || 'Laden fehlgeschlagen'
    store.showToast(store.syncError.value, 'err')
  } finally {
    store.busy.value = false
  }
}

function goEvents() {
  router.push({ name: 'events' })
}
</script>
