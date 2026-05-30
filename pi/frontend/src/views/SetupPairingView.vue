<template>
  <section class="setup-page">
    <div class="setup-card">
      <p class="eyebrow">Vendiqo Raspberry Pi</p>
      <h1>Pi koppeln</h1>
      <p class="muted">
        Erzeugen Sie in der Cloud beim Server-Gerät einen Kopplungscode und geben Sie ihn hier ein.
        Dieser Pi bleibt unter <strong>192.168.192.10</strong> erreichbar.
      </p>

      <div v-if="status?.configured" class="success-box">
        <strong>Bereits gekoppelt.</strong>
        <span>Edge-Client-ID: {{ status.edge_client_id }}</span>
        <span v-if="!status.can_unpair" class="hint-inline">
          Erneutes Koppeln ist gesperrt. Entkoppeln Sie den Pi nur mit dem Werksschlüssel (Support).
        </span>
      </div>

      <form v-if="!status?.configured" class="setup-form" @submit.prevent="pair">
        <label v-if="status?.allow_cloud_url_override">
          Cloud API
          <input v-model="cloudBaseUrl" type="url" required placeholder="https://api.vendiqo.ch" />
        </label>
        <p v-else-if="status" class="cloud-fixed muted">
          Cloud API: <strong>{{ status.cloud_base_url }}</strong>
        </p>
        <label>
          Kopplungscode
          <input
            v-model="pairingCode"
            inputmode="numeric"
            autocomplete="one-time-code"
            required
            placeholder="123-456"
          />
        </label>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Kopple...' : 'Pi koppeln' }}
        </button>
      </form>

      <form
        v-if="status?.configured && status?.can_unpair"
        class="setup-form unpair-form"
        @submit.prevent="unpair"
      >
        <h2>Entkoppeln</h2>
        <p class="muted">
          Entfernt die lokal gespeicherten Edge-Zugangsdaten. Danach kann der Pi erneut gekoppelt werden.
        </p>
        <label>
          Werksschlüssel
          <input
            v-model="unpairSecret"
            type="password"
            autocomplete="off"
            required
            placeholder="PI_SETUP_UNPAIR_SECRET"
          />
        </label>
        <button type="submit" class="danger" :disabled="unpairLoading">
          {{ unpairLoading ? 'Entkopple...' : 'Pi entkoppeln' }}
        </button>
      </form>

      <p v-if="message" class="message" :class="messageType">{{ message }}</p>
      <p class="hint">
        Nach erfolgreicher Kopplung speichert der Pi die Edge-Zugangsdaten lokal und beginnt mit der Cloud-Synchronisation.
      </p>
      <p class="version-line">Vendiqo Pi {{ label }}</p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useAppVersion } from '../composables/useAppVersion'

const { label } = useAppVersion()

const router = useRouter()
const status = ref(null)
const cloudBaseUrl = ref('https://api.vendiqo.ch')
const pairingCode = ref('')
const unpairSecret = ref('')
const loading = ref(false)
const unpairLoading = ref(false)
const message = ref('')
const messageType = ref('')

async function loadStatus() {
  try {
    status.value = await api('/v1/setup/status')
    cloudBaseUrl.value = status.value.cloud_base_url || cloudBaseUrl.value
  } catch {
    status.value = null
  }
}

async function pair() {
  loading.value = true
  message.value = ''
  try {
    const body = {
      pairing_code: pairingCode.value,
      device_name: 'vendiqo-pi',
    }
    if (status.value?.allow_cloud_url_override) {
      body.cloud_base_url = cloudBaseUrl.value
    }
    const result = await api('/v1/setup/pair', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    status.value = result
    message.value = 'Pi wurde erfolgreich gekoppelt. Die Synchronisation startet automatisch.'
    messageType.value = 'success'
    window.setTimeout(() => router.push({ name: 'events' }), 1200)
  } catch (err) {
    message.value = err.message || 'Kopplung fehlgeschlagen.'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function unpair() {
  unpairLoading.value = true
  message.value = ''
  try {
    status.value = await api('/v1/setup/unpair', {
      method: 'POST',
      body: JSON.stringify({ unpair_secret: unpairSecret.value }),
    })
    unpairSecret.value = ''
    pairingCode.value = ''
    message.value = 'Pi wurde entkoppelt. Sie können jetzt erneut koppeln.'
    messageType.value = 'success'
  } catch (err) {
    message.value = err.message || 'Entkoppeln fehlgeschlagen.'
    messageType.value = 'error'
  } finally {
    unpairLoading.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.setup-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: #f4f6fb;
}

.setup-card {
  width: min(100%, 34rem);
  padding: 2rem;
  border-radius: 1.25rem;
  background: white;
  box-shadow: 0 18px 55px rgb(15 23 42 / 14%);
}

.eyebrow {
  margin: 0 0 0.5rem;
  color: #2563eb;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 0.75rem;
}

h2 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.muted,
.hint {
  color: #64748b;
  line-height: 1.5;
}

.hint-inline {
  font-size: 0.9rem;
  line-height: 1.4;
}

.cloud-fixed {
  margin: 0;
}

.setup-form {
  display: grid;
  gap: 1rem;
  margin-top: 1.5rem;
}

.unpair-form {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

label {
  display: grid;
  gap: 0.4rem;
  color: #334155;
  font-weight: 700;
}

input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  font: inherit;
  padding: 0.85rem 1rem;
}

button {
  border: 0;
  border-radius: 0.85rem;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 0.95rem 1rem;
}

button.danger {
  background: #b91c1c;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.success-box {
  display: grid;
  gap: 0.25rem;
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.85rem;
  background: #dcfce7;
  color: #166534;
}

.message {
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 0.85rem;
}

.message.success {
  background: #dcfce7;
  color: #166534;
}

.message.error {
  background: #fee2e2;
  color: #991b1b;
}

.version-line {
  margin: 1.5rem 0 0;
  color: #94a3b8;
  font-size: 0.8rem;
  text-align: center;
}
</style>
