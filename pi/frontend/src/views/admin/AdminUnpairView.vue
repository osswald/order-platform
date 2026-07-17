<template>
  <div>
    <h1>Gerät entkoppeln</h1>
    <p class="muted">Pi von der Cloud trennen und SD-Karte sperren.</p>

    <div v-if="!canUnpair" class="card">
      <p class="muted">Entkoppeln ist für dieses Gerät nicht verfügbar.</p>
    </div>

    <div v-else class="card">
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

    <button type="button" class="btn" style="width: 100%; margin-top: 1.5rem" @click="goBack">Zurück</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useAdminSession } from '@/composables/useAdminSession'
import type { SetupStatusResponse } from '@/types/api'
import { getErrorMessage } from '@/types/api'

const router = useRouter()
const { clearAdminSession } = useAdminSession()
const setupStatus = ref<SetupStatusResponse | null>(null)
const unpairSecret = ref('')
const unpairLoading = ref(false)
const unpairMessage = ref('')
const unpairOk = ref(true)

const canUnpair = computed(
  () => Boolean(setupStatus.value?.configured && setupStatus.value?.can_unpair),
)

onMounted(async () => {
  try {
    setupStatus.value = await api<SetupStatusResponse>('/v1/setup/status')
  } catch {
    /* Pi unreachable */
  }
})

async function uncoupleDevice() {
  if (!canUnpair.value) return
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
    setupStatus.value = await api<SetupStatusResponse>('/v1/setup/unpair', {
      method: 'POST',
      body: JSON.stringify({ unpair_secret: unpairSecret.value }),
    })
    unpairSecret.value = ''
    unpairOk.value = true
    unpairMessage.value = 'Gerät erfolgreich entkoppelt.'
    clearAdminSession()
    window.setTimeout(() => router.replace({ name: 'setup' }), 600)
  } catch (error: unknown) {
    unpairOk.value = false
    unpairMessage.value = getErrorMessage(error, 'Entkoppeln fehlgeschlagen.')
  } finally {
    unpairLoading.value = false
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
</style>
