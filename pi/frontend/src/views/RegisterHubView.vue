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

      <section v-if="openOrders.length" class="open-orders">
        <h2>Offene Bestellungen</h2>
        <ul class="order-list">
          <li v-for="o in openOrders" :key="o.local_order_id">
            <button type="button" class="order-row" @click="resumePayment(o)">
              <span class="num">{{ o.pickup_code ? `Pickup ${o.pickup_code}` : `Bestellung ${o.local_order_id}` }}</span>
              <span class="meta muted">{{ o.item_count }} Position(en) · {{ formatMoney(o.total_cents, currency) }}</span>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <footer class="screen-footer">
      <button type="button" class="btn" @click="switchRegister">Kasse wechseln</button>
      <button type="button" class="btn" @click="router.push({ name: 'events' })">Event wechseln</button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TestBetriebPill from '@/components/TestBetriebPill.vue'
import { api } from '@/api'
import { useCart } from '@/composables/useCart'
import { useRegisterDisplay } from '@/composables/useRegisterDisplay'
import { useRegisterSession } from '@/composables/useRegisterSession'
import { ensureShiftForSubject, maybeEndShiftOnSwitch } from '@/composables/useShiftSession'
import { isEventTest } from '@/utils/eventStatus'
import { formatMoney } from '@/utils/money'
import type { RegisterOpenOrderRow, RegisterOpenOrdersResponse } from '@/types/api'
import { useEventContext } from '@/composables/useEventContext'

const router = useRouter()
const route = useRoute()
const { clearCart } = useCart()
const { register, event, setDisplayIdle, clearPickupHold, orderRoute } = useRegisterDisplay()
const { setRegisterSession } = useRegisterSession()
const { currency } = useEventContext()
const isTest = computed(() => isEventTest(event.value?.status as string | undefined))
const openOrders = ref<RegisterOpenOrderRow[]>([])

function refreshHubDisplay() {
  if (route.name !== 'register-hub' || !register.value) return
  setDisplayIdle()
}

async function loadOpenOrders() {
  const ev = event.value
  const reg = register.value
  if (!ev?.id || !reg) return
  try {
    const r = await api<RegisterOpenOrdersResponse>(
      `/v1/registers/${reg.uuid}/open-orders?event_id=${ev.id}`,
    )
    openOrders.value = r.orders || []
  } catch {
    openOrders.value = []
  }
}

function startOrder() {
  clearPickupHold()
  clearCart()
  router.push(orderRoute())
}

function resumePayment(o: RegisterOpenOrderRow) {
  const reg = register.value
  if (!reg) return
  router.push({
    name: 'register-pay',
    params: { registerUuid: String(reg.uuid), orderId: String(o.local_order_id) },
  })
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

watch(
  () => route.name,
  () => {
    refreshHubDisplay()
    if (route.name === 'register-hub') loadOpenOrders()
  },
)

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
  await loadOpenOrders()
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
.open-orders h2 {
  font-size: 1rem;
  margin: 0.5rem 0 0.25rem;
}
.order-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.order-list li {
  margin-bottom: 0.5rem;
}
.order-row {
  width: 100%;
  text-align: left;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.order-row .num {
  font-weight: 600;
  font-size: 1.1rem;
}
</style>
