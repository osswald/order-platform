<template>
  <div v-if="unreachable" class="card pi-unreachable-banner" role="alert">
    <p>
      <strong>Keine Verbindung zur Kasse (Pi)</strong>
      — Netzwerk prüfen oder erneut versuchen.
    </p>
    <div class="banner-actions">
      <button type="button" class="btn primary" :disabled="probing" @click="onRetry">
        {{ probing ? 'Prüfe…' : 'Erneut prüfen' }}
      </button>
      <button type="button" class="btn" @click="onChangeConnection">Verbindung ändern</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { usePiConnectivity } from '@/composables/usePiConnectivity'

const router = useRouter()
const { unreachable, probing, probeNow } = usePiConnectivity()

async function onRetry() {
  await probeNow()
}

function onChangeConnection() {
  router.push({ name: 'connection-setup' })
}
</script>

<style scoped>
.pi-unreachable-banner {
  margin-top: 1rem;
  padding: 1rem;
  border-color: var(--err, #c62828);
  background: color-mix(in srgb, var(--err, #c62828) 8%, var(--card));
}
.pi-unreachable-banner p {
  margin: 0 0 0.75rem;
}
.banner-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
