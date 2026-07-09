<template>
  <div>
    <h1>
      {{ register?.name || 'Kasse' }}
      <TestBetriebPill v-if="isTest" />
    </h1>
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

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TestBetriebPill from '@/components/TestBetriebPill.vue'
import { useCart } from '@/composables/useCart'
import { useRegisterDisplay } from '@/composables/useRegisterDisplay'
import { useRegisterSession } from '@/composables/useRegisterSession'
import { ensureShiftForSubject, maybeEndShiftOnSwitch } from '@/composables/useShiftSession'
import { isEventTest } from '@/utils/eventStatus'

const router = useRouter()
const route = useRoute()
const { clearCart } = useCart()
const { register, event, setDisplayIdle, clearPickupHold, orderRoute } = useRegisterDisplay()
const { setRegisterSession } = useRegisterSession()
const isTest = computed(() => isEventTest(event.value?.status as string | undefined))

function refreshHubDisplay() {
  if (route.name !== 'register-hub' || !register.value) return
  setDisplayIdle()
}

function startOrder() {
  clearPickupHold()
  clearCart()
  router.push(orderRoute())
}

async function switchRegister() {
  const ev = event.value
  const regUuid = register.value?.uuid
  if (!ev?.id || !regUuid) return
  const ok = await maybeEndShiftOnSwitch({
    event: ev,
    eventId: ev.id,
    subjectType: 'cash_register',
    cashRegisterUuid: String(regUuid),
  })
  if (!ok) return
  setRegisterSession(null)
  router.push({ name: 'registers' })
}

watch(() => route.name, refreshHubDisplay)

onMounted(async () => {
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  const ev = event.value
  const reg = register.value
  if (!ev?.id) {
    router.replace({ name: 'registers' })
    return
  }
  try {
    await ensureShiftForSubject({
      event: ev,
      eventId: ev.id,
      subjectType: 'cash_register',
      cashRegisterUuid: String(reg.uuid),
    })
  } catch {
    router.replace({ name: 'registers' })
    return
  }
  refreshHubDisplay()
})
</script>

<style scoped>
h1 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
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
.small {
  font-size: 0.85rem;
}
</style>
