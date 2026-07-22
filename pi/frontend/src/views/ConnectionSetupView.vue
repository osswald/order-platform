<template>
  <section class="setup-page">
    <div class="setup-card">
      <p class="eyebrow">Vendiqo Waiter</p>
      <h1>Pi-Verbindung</h1>
      <p class="muted">
        Der Pi ist unter der Standard-Adresse nicht erreichbar. Geben Sie die Pi-API-Basis-URL ein
        (z.&nbsp;B. <strong>http://192.168.192.10</strong>).
      </p>

      <form class="setup-form" @submit.prevent="save">
        <label>
          Pi-API Basis-URL
          <input
            v-model="apiUrl"
            type="text"
            inputmode="url"
            autocomplete="off"
            required
            placeholder="http://192.168.192.10"
          />
        </label>
        <div class="actions">
          <button type="button" class="btn" :disabled="testing" @click="testConnection">
            {{ testing ? 'Teste…' : 'Verbindung testen' }}
          </button>
          <button type="submit" class="btn primary" :disabled="!canSave || saving">
            {{ saving ? 'Speichere…' : 'Speichern und fortfahren' }}
          </button>
        </div>
      </form>

      <button type="button" class="btn demo-btn" :disabled="testing" @click="usePlayReviewDemo">
        Demo
      </button>

      <p v-if="message" class="message" :class="messageType">{{ message }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getApiBase, setApiBase } from '@/api'
import { PLAY_REVIEW_DEMO_API_BASE, probeApiBase } from '@/utils/probeApiBase'

const router = useRouter()
const apiUrl = ref('')
const testedOk = ref(false)
const testing = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref<'ok' | 'err'>('ok')

const canSave = computed(() => testedOk.value && apiUrl.value.trim().length > 0)

onMounted(() => {
  apiUrl.value = getApiBase()
})

async function testConnection() {
  message.value = ''
  testedOk.value = false
  testing.value = true
  try {
    const result = await probeApiBase(apiUrl.value)
    if (result.reachable) {
      testedOk.value = true
      message.value = 'Verbindung OK.'
      messageType.value = 'ok'
    } else if (result.reason === 'network') {
      message.value = 'Pi nicht erreichbar. Netzwerk und URL prüfen.'
      messageType.value = 'err'
    } else {
      message.value = result.message || 'Pi antwortet mit Fehler.'
      messageType.value = 'err'
    }
  } finally {
    testing.value = false
  }
}

async function usePlayReviewDemo() {
  apiUrl.value = PLAY_REVIEW_DEMO_API_BASE
  await testConnection()
  // Play Console / reviewer instructions say tap Demo then continue — save on success.
  if (testedOk.value) {
    await save()
  }
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  message.value = ''
  try {
    setApiBase(apiUrl.value.trim())
    await router.replace({ name: 'events' })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.setup-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
}

.setup-card {
  width: min(100%, 28rem);
}

.eyebrow {
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 0.5rem;
}

.setup-form label {
  display: block;
  margin-bottom: 1rem;
}

.setup-form input {
  width: 100%;
  margin-top: 0.35rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.demo-btn {
  width: 100%;
  margin-top: 1rem;
}

.message {
  margin-top: 1rem;
}

.message.ok {
  color: var(--ok);
}

.message.err {
  color: var(--danger);
}
</style>
