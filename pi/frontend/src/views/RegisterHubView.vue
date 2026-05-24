<template>
  <div>
    <h1>{{ register?.name || 'Kasse' }}</h1>
    <p class="muted">{{ event?.name }}</p>
    <p v-if="register?.pickup_code_prefix" class="muted small">Pickup {{ register.pickup_code_prefix }}</p>

    <div v-if="!register" class="card">
      <p>Kasse nicht gefunden.</p>
      <RouterLink :to="{ name: 'registers' }">Zurück</RouterLink>
    </div>

    <div v-else class="hub-actions">
      <button type="button" class="btn primary hub-btn" @click="startOrder">
        Neue Bestellung
      </button>
      <button type="button" class="btn hub-btn" @click="openDisplay">
        Kundendisplay
      </button>
      <div class="display-url card">
        <label class="url-label">Kundendisplay-URL</label>
        <code class="url-text">{{ displayUrl }}</code>
        <button type="button" class="btn" @click="copyDisplayUrl">
          URL kopieren
        </button>
      </div>
    </div>

    <p class="muted footer-links">
      <RouterLink :to="{ name: 'registers' }">Kassen wechseln</RouterLink>
      ·
      <RouterLink :to="{ name: 'events' }">Event wechseln</RouterLink>
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCart } from '../composables/useCart'
import { useRegisterDisplay } from '../composables/useRegisterDisplay'

const route = useRoute()
const router = useRouter()
const { clearCart } = useCart()
const { register, event, registerDisplayUrl, updateDisplay, orderRoute, displayRoute } = useRegisterDisplay()

const displayUrl = computed(() => registerDisplayUrl())

function startOrder() {
  clearCart()
  router.push(orderRoute())
}

function openDisplay() {
  router.push(displayRoute())
}

async function copyDisplayUrl() {
  const url = displayUrl.value
  try {
    await navigator.clipboard.writeText(url)
    store.showToast('URL kopiert.', 'ok')
  } catch {
    store.showToast(url, 'ok')
  }
}

onMounted(() => {
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  if (route.query.fresh === '1') {
    updateDisplay({
      state: 'idle',
      lines: [],
      total_cents: 0,
      show_twint: false,
      twint_qr_data_url: null,
    })
  }
})
</script>

<style scoped>
.hub-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}
.hub-btn {
  width: 100%;
  min-height: 56px;
  font-size: 1.1rem;
}
.display-url {
  margin-top: 0.5rem;
  padding: 0.85rem 1rem;
}
.url-label {
  display: block;
  font-size: 0.85rem;
  color: var(--muted);
  margin-bottom: 0.35rem;
}
.url-text {
  display: block;
  word-break: break-all;
  font-size: 0.8rem;
  margin-bottom: 0.75rem;
}
.small {
  font-size: 0.85rem;
}
.footer-links {
  margin-top: 1.5rem;
}
</style>
