<template>
  <div class="pickup-screen">
    <p v-if="error" class="error">{{ error }}</p>

    <div class="pickup-columns">
      <section class="pickup-column pending">
        <h2>In Arbeit</h2>
        <div class="code-grid">
          <article v-for="order in pendingOrders" :key="order.local_order_id" class="pickup-code">
            {{ order.pickup_code }}
          </article>
        </div>
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
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useEventContext } from '../composables/useEventContext'
import { api } from '../api'

const orders = ref([])
const error = ref('')
let pollTimer = null

const { event } = useEventContext()
const pendingOrders = computed(() => orders.value.filter((o) => o.pickup_status !== 'ready'))
const readyOrders = computed(() =>
  orders.value
    .filter((o) => o.pickup_status === 'ready')
    .sort((a, b) => new Date(a.ready_at || 0) - new Date(b.ready_at || 0)),
)

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
  box-sizing: border-box;
  height: 100dvh;
  padding: 1rem;
  background: #0d1117;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.pickup-columns {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.pickup-column {
  min-height: 0;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.06);
  overflow-y: auto;
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
  margin: 0 0 0.75rem;
}
@media (max-width: 800px) {
  .pickup-columns {
    grid-template-columns: 1fr;
  }
}
</style>
