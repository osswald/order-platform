<template>
  <div>
    <h1>{{ register?.name || 'Kasse' }}</h1>
    <p class="muted">{{ event?.name }}</p>
    <p v-if="register?.pickup_code_prefix" class="muted small">Pickup {{ register.pickup_code_prefix }}</p>

    <div v-if="!register" class="card">
      <p>Kasse nicht gefunden.</p>
    </div>

    <div v-else class="hub-actions">
      <button type="button" class="btn primary hub-btn" @click="startOrder">
        Neue Bestellung
      </button>
    </div>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="switchRegister">Kasse wechseln</button>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCart } from '../composables/useCart'
import { useRegisterDisplay } from '../composables/useRegisterDisplay'
import { useRegisterSession } from '../composables/useRegisterSession'

const router = useRouter()
const route = useRoute()
const { clearCart } = useCart()
const { register, setDisplayIdle, clearPickupHold, orderRoute } = useRegisterDisplay()
const { setRegisterSession } = useRegisterSession()

function refreshHubDisplay() {
  if (route.name !== 'register-hub' || !register.value) return
  setDisplayIdle()
}

function startOrder() {
  clearPickupHold()
  clearCart()
  router.push(orderRoute())
}

function switchRegister() {
  setRegisterSession(null)
  router.push({ name: 'registers' })
}

watch(() => route.name, refreshHubDisplay)

onMounted(() => {
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  refreshHubDisplay()
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
.small {
  font-size: 0.85rem;
}
</style>
