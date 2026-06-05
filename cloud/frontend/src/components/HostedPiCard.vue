<template>
  <v-card class="hosted-pi-card" variant="outlined">
    <v-card-title>Cloud-Pi (Test)</v-card-title>
    <v-card-text>
      <p class="hosted-pi-desc">
        Starten Sie eine temporäre Pi-Instanz im Browser, um die Konfiguration zu testen.
        Läuft maximal 24 Stunden; emulierte Belege erscheinen neben der App (Desktop) oder über den Belege-Button (Mobil).
      </p>

      <p v-if="error" class="hosted-pi-error">{{ error }}</p>

      <div v-if="loading && !instance" class="hosted-pi-status">
        <v-progress-circular indeterminate size="20" width="2" />
        <span>Laden…</span>
      </div>

      <template v-else-if="isActive">
        <p class="hosted-pi-status">
          <v-chip color="success" size="small" variant="tonal">{{ statusLabel }}</v-chip>
          <span v-if="expiresLabel" class="hosted-pi-expiry"> · {{ expiresLabel }}</span>
        </p>
        <div class="hosted-pi-actions">
          <v-btn
            v-if="instance?.url && instance?.status === 'running'"
            color="primary"
            variant="flat"
            type="button"
            @click="openInstance"
          >
            Öffnen
          </v-btn>
          <v-btn variant="outlined" type="button" :disabled="loading" @click="onStop">
            Beenden
          </v-btn>
        </div>
      </template>

      <template v-else-if="instance?.status === 'failed'">
        <p class="hosted-pi-error">{{ instance.last_error || 'Start fehlgeschlagen.' }}</p>
        <v-btn color="primary" variant="flat" type="button" :disabled="loading" @click="onStart">
          Erneut starten
        </v-btn>
      </template>

      <template v-else>
        <v-btn color="primary" variant="flat" type="button" :disabled="loading" @click="onStart">
          Starten
        </v-btn>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useHostedPi } from '../composables/useHostedPi'

const props = defineProps({
  eventId: { type: Number, required: true },
})

const { instance, loading, error, load, start, stop } = useHostedPi(computed(() => props.eventId))

const activeStatuses = new Set(['provisioning', 'running', 'stopping'])

const isActive = computed(() => activeStatuses.has(instance.value?.status))

const statusLabel = computed(() => {
  const status = instance.value?.status
  if (status === 'provisioning') return 'Wird gestartet…'
  if (status === 'running') return 'Läuft'
  if (status === 'stopping') return 'Wird beendet…'
  return status || 'Unbekannt'
})

const expiresLabel = computed(() => {
  const expires = instance.value?.expires_at
  if (!expires) return ''
  const diffMs = new Date(expires).getTime() - Date.now()
  if (diffMs <= 0) return 'läuft ab'
  const hours = Math.floor(diffMs / (60 * 60 * 1000))
  const minutes = Math.floor((diffMs % (60 * 60 * 1000)) / (60 * 1000))
  if (hours > 0) return `noch ${hours}h ${minutes}m`
  return `noch ${minutes}m`
})

let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (isActive.value || instance.value?.status === 'provisioning') {
      load()
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function onStart() {
  await start()
  startPolling()
}

async function onStop() {
  await stop()
  stopPolling()
}

function openInstance() {
  if (instance.value?.url) {
    window.open(instance.value.url, '_blank', 'noopener,noreferrer')
  }
}

watch(
  () => props.eventId,
  () => {
    load().then(() => {
      if (isActive.value) startPolling()
    })
  },
)

onMounted(async () => {
  await load()
  if (isActive.value) startPolling()
})

onUnmounted(stopPolling)
</script>

<style scoped>
.hosted-pi-card {
  margin-bottom: 1rem;
}
.hosted-pi-desc {
  margin: 0 0 1rem;
  color: rgba(var(--v-theme-on-surface), 0.7);
}
.hosted-pi-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.hosted-pi-expiry {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.9rem;
}
.hosted-pi-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.hosted-pi-error {
  color: rgb(var(--v-theme-error));
  margin-bottom: 0.75rem;
}
</style>
