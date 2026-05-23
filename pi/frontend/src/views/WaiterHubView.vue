<template>
  <div>
    <h1>Kellner</h1>
    <p class="muted">{{ event?.name }} · {{ waiter?.name }}</p>

    <div class="hub-actions">
      <button type="button" class="btn primary hub-btn" @click="router.push({ name: 'table-new' })">
        Neue Bestellung
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'table-settle-keypad' })">
        Tisch abrechnen
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'tables-open' })">
        Offene Tische
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'collective-open' })">
        Sammelrechnungen
      </button>
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'stock' })">
        Lagerbestand
      </button>
    </div>

    <p class="muted footer-links">
      <button type="button" class="link-btn" @click="switchWaiter">Kellner wechseln</button>
      ·
      <RouterLink :to="{ name: 'events' }">Event wechseln</RouterLink>
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import * as store from '../store'

const router = useRouter()
const event = computed(() => store.selectedEvent.value)
const waiter = computed(() => store.waiter.value)

function switchWaiter() {
  store.setWaiter(null)
  router.push({ name: 'login' })
}
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
.footer-links {
  margin-top: 1.5rem;
}
.link-btn {
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
  text-decoration: underline;
}
</style>
