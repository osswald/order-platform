<template>
  <div>
    <h1>Kassen</h1>
    <p class="muted">{{ event?.name || 'Event' }}</p>

    <div v-if="!registers.length" class="card">
      <p>Für dieses Event sind keine Kassen konfiguriert.</p>
      <RouterLink :to="{ name: 'events' }">Zurück zu Events</RouterLink>
    </div>

    <div v-else class="hub-actions">
      <button
        v-for="reg in registers"
        :key="reg.uuid"
        type="button"
        class="btn primary hub-btn"
        @click="openRegister(reg)"
      >
        {{ reg.name }}
        <span class="muted small">Pickup {{ reg.pickup_code_prefix }}</span>
      </button>
    </div>

    <div class="hub-actions secondary-actions">
      <button type="button" class="btn hub-btn" @click="router.push({ name: 'pickup' })">
        Pickup Screen
      </button>
      <RouterLink :to="{ name: 'events' }">Event wechseln</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCart } from '../composables/useCart'
import { useEventContext } from '../composables/useEventContext'

const router = useRouter()
const { event } = useEventContext()
const { clearCart } = useCart()
const registers = computed(() =>
  (event.value?.configuration?.cash_registers || []).slice().sort((a, b) => {
    const so = (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0)
    return so || String(a.name || '').localeCompare(String(b.name || ''))
  }),
)

function openRegister(reg) {
  clearCart()
  router.push({ name: 'register-hub', params: { registerUuid: reg.uuid }, query: { fresh: '1' } })
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
.hub-btn .small {
  display: block;
  font-size: 0.8rem;
  margin-top: 0.2rem;
}
.secondary-actions {
  margin-top: 1.5rem;
}
</style>
