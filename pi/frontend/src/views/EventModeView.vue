<template>
  <div class="screen-page">
    <h1>Modus wählen</h1>
    <p class="muted">{{ event?.name }}</p>

    <div class="hub-actions">
      <button type="button" class="btn primary hub-btn" @click="goWaiter">Kellner</button>
      <button type="button" class="btn hub-btn" @click="goRegister">Kasse</button>
    </div>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Anderes Event</button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useEventContext } from '@/composables/useEventContext'
import { setRegisterSession } from '@/store'

const router = useRouter()
const { event, setWaiter } = useEventContext()

function goWaiter() {
  setRegisterSession(null)
  setWaiter(null)
  router.push({ name: 'login' })
}

function goRegister() {
  setWaiter(null)
  setRegisterSession(null)
  router.push({ name: 'registers' })
}
</script>

<style scoped>
.screen-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 2rem);
}
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
</style>
