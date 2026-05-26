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
      </div>

      <form class="setup-form" @submit.prevent="pair">
        <label>
          Cloud API
          <input v-model="cloudBaseUrl" type="url" required placeholder="https://api.vendiqo.ch" />
        </label>
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

      <p v-if="message" class="message" :class="messageType">{{ message }}</p>
      <p class="hint">
        Nach erfolgreicher Kopplung speichert der Pi die Edge-Zugangsdaten lokal und beginnt mit der Cloud-Synchronisation.
      </p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const status = ref(null)
const cloudBaseUrl = ref('https://api.vendiqo.ch')
const pairingCode = ref('')
const loading = ref(false)
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
    const result = await api('/v1/setup/pair', {
      method: 'POST',
      body: JSON.stringify({
        cloud_base_url: cloudBaseUrl.value,
        pairing_code: pairingCode.value,
        device_name: 'vendiqo-pi',
      }),
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

.muted,
.hint {
  color: #64748b;
  line-height: 1.5;
}

.setup-form {
  display: grid;
  gap: 1rem;
  margin-top: 1.5rem;
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
</style>
