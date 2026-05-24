<template>
  <div class="customer-display">
    <section v-if="payload.state === 'submitted'" class="pickup-done">
      <p>Danke!</p>
      <strong>Pickup {{ payload.pickup_code }}</strong>
      <span>Bitte Bon mitnehmen.</span>
    </section>

    <section v-else-if="payload.state === 'twint' || payload.show_twint" class="twint-panel">
      <div class="twint-info">
        <h2>TWINT</h2>
        <p class="twint-amount">{{ formatAmount(payload.total_cents || 0) }}</p>
        <p v-if="!payload.twint_qr_data_url" class="muted">Bitte mit TWINT bezahlen.</p>
      </div>
      <div v-if="payload.twint_qr_data_url" class="twint-qr">
        <img :src="payload.twint_qr_data_url" alt="TWINT QR-Code" class="qr-image" />
      </div>
    </section>

    <section v-else-if="payload.state === 'ordering'" class="order-preview">
      <div class="order-body">
        <h2>Ihre Bestellung</h2>
        <p v-if="!lines.length" class="muted">Noch keine Artikel.</p>
        <ul v-else>
          <li v-for="line in lines" :key="line.lineId || `${line.article_id}-${line.qty}`">
            <span>{{ Math.max(1, Number(line.qty) || 1) }}x {{ articleName(line.article_id) }}</span>
            <span>{{ lineTotal(line) }}</span>
            <span
              v-for="add in additionLabelsFor(line)"
              :key="add.id"
              class="addition"
            >+ {{ add.name }}</span>
          </li>
        </ul>
      </div>
      <footer class="order-total">
        <span>Total</span>
        <strong>{{ formatAmount(payload.total_cents || 0) }}</strong>
      </footer>
    </section>

    <section v-else class="idle-screen">
      <p class="welcome">Herzlich Willkommen</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatAmount, lineTotalCents } from '../utils/money'
import { lineAdditionLabels } from '../utils/bundleHelpers'

const route = useRoute()
const payload = ref({})
let pollTimer = null

const event = computed(() => store.selectedEvent.value)
const registerUuid = computed(() => String(route.params.registerUuid || ''))
const lines = computed(() => payload.value.lines || [])
const articles = computed(() => event.value?.articles || {})

function articleName(id) {
  return store.articleName(id)
}

function lineTotal(line) {
  return formatAmount(lineTotalCents(line, articles.value))
}

function additionLabelsFor(line) {
  return lineAdditionLabels(line, articles.value)
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
  box-sizing: border-box;
  height: 100dvh;
  overflow: hidden;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  display: flex;
  flex-direction: column;
  background: #101418;
  color: #fff;
}
.muted {
  color: #b8c1cc;
}
.order-preview,
.pickup-done,
.twint-panel,
.idle-screen {
  flex: 1;
  min-height: 0;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 1.5rem;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  background: rgba(255, 255, 255, 0.06);
}
.idle-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.welcome {
  margin: 0;
  font-size: clamp(2rem, 8vw, 4.5rem);
  font-weight: 600;
  line-height: 1.2;
}
.order-preview {
  display: flex;
  flex-direction: column;
}
.order-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.order-preview h2,
.twint-panel h2 {
  margin-top: 0;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
li {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  padding: 0.8rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  font-size: clamp(1rem, 2.5vw, 1.75rem);
}
.addition {
  width: 100%;
  font-size: 0.75em;
  color: #b8c1cc;
}
.order-total {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 2px solid rgba(255, 255, 255, 0.24);
  font-size: clamp(1.5rem, 4vw, 2.75rem);
}
.order-total strong {
  font-size: clamp(1.8rem, 5vw, 3.25rem);
}
.twint-panel {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 1rem;
}
.twint-info {
  flex: 0 0 38%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.twint-amount {
  font-size: clamp(1.75rem, 5vw, 3.5rem);
  font-weight: 700;
  margin: 0.5rem 0 0;
}
.twint-qr {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
.qr-image {
  max-height: calc(100dvh - 2rem);
  max-width: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
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

@media (orientation: portrait) {
  .twint-panel {
    flex-direction: column;
    justify-content: center;
  }
  .twint-info {
    flex: 0 0 auto;
    width: 100%;
    text-align: center;
  }
  .twint-qr {
    flex: 1;
    width: 100%;
  }
}
</style>
