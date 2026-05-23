<template>
  <div class="customer-display">
    <header>
      <h1>{{ payload.register_name || register?.name || 'Kasse' }}</h1>
      <p class="muted">{{ event?.name || 'Event' }}</p>
    </header>

    <section v-if="payload.state === 'submitted'" class="pickup-done">
      <p>Danke!</p>
      <strong>Pickup {{ payload.pickup_code }}</strong>
      <span>Bitte Bon mitnehmen.</span>
    </section>

    <section v-else class="order-preview">
      <h2>Ihre Bestellung</h2>
      <p v-if="!lines.length" class="muted">Noch keine Artikel.</p>
      <ul v-else>
        <li v-for="line in lines" :key="line.lineId || `${line.article_id}-${line.qty}`">
          <span>{{ Math.max(1, Number(line.qty) || 1) }}x {{ articleName(line.article_id) }}</span>
          <span>{{ lineTotal(line) }}</span>
        </li>
      </ul>
      <div class="total">
        <span>Total</span>
        <strong>{{ formatAmount(payload.total_cents || 0) }}</strong>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatAmount, lineTotalCents } from '../utils/money'

const route = useRoute()
const payload = ref({})
let pollTimer = null

const event = computed(() => store.selectedEvent.value)
const registerUuid = computed(() => String(route.params.registerUuid || ''))
const register = computed(() =>
  (event.value?.configuration?.cash_registers || []).find((reg) => String(reg.uuid) === registerUuid.value) || null,
)
const lines = computed(() => payload.value.lines || [])
const articles = computed(() => event.value?.articles || {})

function articleName(id) {
  return store.articleName(id)
}

function lineTotal(line) {
  return formatAmount(lineTotalCents(line, articles.value))
}

async function loadDisplay() {
  if (!event.value?.id || !registerUuid.value) return
  try {
    const data = await api(`/v1/registers/${encodeURIComponent(registerUuid.value)}/display?event_id=${encodeURIComponent(event.value.id)}`)
    payload.value = data?.payload || {}
  } catch {
    payload.value = {}
  }
}

onMounted(() => {
  loadDisplay()
  pollTimer = setInterval(loadDisplay, 1000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.customer-display {
  min-height: 100vh;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  background: #101418;
  color: #fff;
}
.muted {
  color: #b8c1cc;
}
h1 {
  font-size: clamp(2rem, 5vw, 4rem);
  margin: 0;
}
.order-preview,
.pickup-done {
  flex: 1;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 1.5rem;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.06);
}
.order-preview h2 {
  margin-top: 0;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
li,
.total {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  font-size: clamp(1.2rem, 3vw, 2rem);
}
.total {
  margin-top: 1.5rem;
  border-bottom: none;
  font-size: clamp(1.8rem, 5vw, 3.5rem);
}
.pickup-done {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
}
.pickup-done p {
  font-size: clamp(1.8rem, 4vw, 3rem);
  margin: 0;
}
.pickup-done strong {
  font-size: clamp(4rem, 14vw, 10rem);
  line-height: 1;
}
.pickup-done span {
  font-size: clamp(1.2rem, 3vw, 2rem);
}
</style>
