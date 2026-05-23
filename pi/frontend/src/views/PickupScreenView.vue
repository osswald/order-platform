<template>
  <div class="pickup-screen">
    <header class="pickup-header">
      <div>
        <h1>Pickup</h1>
        <p class="muted">{{ event?.name || 'Event' }}</p>
      </div>
      <RouterLink class="btn small-btn" :to="{ name: 'events' }">Zurück</RouterLink>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="pickup-columns">
      <section class="pickup-column pending">
        <h2>In Arbeit</h2>
        <div class="code-grid">
          <article v-for="order in pendingOrders" :key="order.local_order_id" class="pickup-code">
            {{ order.pickup_code }}
          </article>
        </div>
        <p v-if="!pendingOrders.length" class="muted">Keine offenen Bestellungen.</p>
      </section>

      <section class="pickup-column ready">
        <h2>Bereit</h2>
        <div class="code-grid">
          <button
            v-for="order in readyOrders"
            :key="order.local_order_id"
            type="button"
            class="pickup-code ready-code"
            @click="markPickedUp(order)"
          >
            {{ order.pickup_code }}
          </button>
        </div>
        <p v-if="!readyOrders.length" class="muted">Noch nichts bereit.</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import * as store from '../store'
import { api } from '../api'

const orders = ref([])
const error = ref('')
let pollTimer = null

const event = computed(() => store.selectedEvent.value)
const pendingOrders = computed(() => orders.value.filter((o) => o.pickup_status !== 'ready'))
const readyOrders = computed(() => orders.value.filter((o) => o.pickup_status === 'ready'))

async function loadOrders() {
  if (!event.value?.id) return
  try {
    const data = await api(`/v1/pickup/orders?event_id=${encodeURIComponent(event.value.id)}`)
    orders.value = data?.orders || []
    error.value = ''
  } catch (e) {
    error.value = e.message || 'Pickup Screen konnte nicht geladen werden.'
  }
}

async function markPickedUp(order) {
  try {
    await api(`/v1/pickup/orders/${order.local_order_id}/picked-up`, { method: 'POST' })
    await loadOrders()
  } catch (e) {
    error.value = e.message || 'Konnte nicht abgeschlossen werden.'
  }
}

onMounted(() => {
  loadOrders()
  pollTimer = setInterval(loadOrders, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.pickup-screen {
  min-height: 100vh;
  padding: 1rem;
  background: #0d1117;
  color: #fff;
}
.pickup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}
.muted {
  color: #9aa7b5;
}
.pickup-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.pickup-column {
  min-height: 75vh;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.06);
}
.pickup-column h2 {
  margin-top: 0;
  font-size: clamp(1.5rem, 3vw, 3rem);
}
.code-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}
.pickup-code {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  border: 2px solid rgba(255, 255, 255, 0.18);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.08);
  color: inherit;
  font-size: clamp(2rem, 6vw, 5rem);
  font-weight: 800;
}
.ready-code {
  cursor: pointer;
  background: #1f8f4d;
  border-color: #35c975;
}
.error {
  color: #ff8a8a;
}
@media (max-width: 800px) {
  .pickup-columns {
    grid-template-columns: 1fr;
  }
}
</style>
