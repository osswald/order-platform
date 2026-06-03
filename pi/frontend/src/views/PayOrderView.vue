<template>
  <div>
    <h1>Zahlung</h1>
    <p class="muted">Tisch {{ table }} · Bestellung #{{ orderId }}</p>

    <div v-if="loading" class="muted">Laden…</div>
    <template v-else>
      <ul v-if="orderLines.length" class="pay-lines">
        <li v-for="(line, idx) in orderLines" :key="idx" class="pay-line">
          <div class="pay-line-main">
            <span class="pay-line-name">{{ lineName(line) }}</span>
            <span class="pay-line-total">{{ formatAmount(lineTotalCents(line, articles)) }}</span>
          </div>
          <span
            v-for="add in lineAdditionLabels(line, articles)"
            :key="add.id"
            class="pay-line-addition"
          >+ {{ add.name }}</span>
        </li>
      </ul>

      <div class="card">
        <p>Zu zahlen: <strong>{{ formatAmount(totalCents) }}</strong></p>
        <MoneyKeypad v-model="cashCents" />
        <p v-if="cashMismatch" class="err-text">Betrag muss {{ formatAmount(totalCents) }} sein.</p>
      </div>
      <button
        type="button"
        class="btn primary"
        style="width: 100%"
        :disabled="cashMismatch || paying"
        @click="pay"
      >
        Bezahlen
      </button>
      <button type="button" class="btn" style="width: 100%; margin-top: 0.5rem" @click="goBack">
        Abbrechen
      </button>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useCart } from '../composables/useCart'
import { useEventContext } from '../composables/useEventContext'
import { formatAmount, lineTotalCents } from '../utils/money'
import { lineAdditionLabels } from '../utils/bundleHelpers'
import { resolvePaymentsForAmount } from '../utils/resolvePayment'
import { offerPaymentReceipt } from '../utils/paymentReceiptPrompt'
import MoneyKeypad from '../components/MoneyKeypad.vue'

const route = useRoute()
const router = useRouter()
const { event, showToast } = useEventContext()
const { activeTableNumber, articleName } = useCart()
const orderId = computed(() => route.params.id)
const table = computed(() => route.query.table || activeTableNumber.value)
const totalCents = ref(0)
const cashCents = ref(0)
const loading = ref(true)
const paying = ref(false)
const orderLines = ref([])

const articles = computed(() => event.value?.articles || {})

const cashMismatch = computed(() => cashCents.value !== totalCents.value)

function lineName(line) {
  const qty = Math.max(1, Number(line.qty) || 1)
  const name = articleName(line.article_id)
  return qty > 1 ? `${qty}× ${name}` : name
}

onMounted(async () => {
  const ev = event.value
  if (!ev) {
    router.replace({ name: 'hub' })
    return
  }
  const qTotal = parseInt(String(route.query.total_cents || ''), 10)
  try {
    const summary = await api(`/v1/tables/${table.value}?event_id=${ev.id}`)
    const order = summary.open_orders?.find((o) => String(o.local_order_id) === String(orderId.value))
    orderLines.value = (order?.lines || []).filter((l) => l && l.article_id != null)
    if (Number.isFinite(qTotal) && qTotal > 0) {
      totalCents.value = qTotal
    } else {
      totalCents.value = order?.line_total_cents ?? 0
    }
  } catch {
    orderLines.value = []
    if (Number.isFinite(qTotal) && qTotal > 0) {
      totalCents.value = qTotal
    } else {
      totalCents.value = 0
    }
  }
  cashCents.value = totalCents.value
  loading.value = false
})

async function pay() {
  if (cashMismatch.value) return
  let payments
  try {
    payments = await resolvePaymentsForAmount(
      event.value,
      cashCents.value,
      String(orderId.value),
    )
  } catch (e) {
    if (e?.message !== 'cancelled') {
      showToast(e?.message || 'Zahlung abgebrochen.', 'err')
    }
    return
  }
  paying.value = true
  try {
    const res = await api(`/v1/orders/${orderId.value}/pay`, {
      method: 'POST',
      body: JSON.stringify({ payments }),
    })
    activeTableNumber.value = null
    showToast('Bezahlt.', 'ok')
    if (res.payment_id) {
      await offerPaymentReceipt({
        paymentId: res.payment_id,
        event: event.value,
        showToast,
      })
    }
    router.replace({ name: 'hub' })
  } catch (e) {
    showToast(e.message || 'Zahlung fehlgeschlagen', 'err')
  } finally {
    paying.value = false
  }
}

function goBack() {
  activeTableNumber.value = null
  router.replace({ name: 'hub' })
}
</script>

<style scoped>
.pay-lines {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  overflow: hidden;
}
.pay-line {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--border);
}
.pay-line:last-child {
  border-bottom: none;
}
.pay-line-main {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
}
.pay-line-name {
  font-weight: 500;
}
.pay-line-total {
  font-variant-numeric: tabular-nums;
}
.pay-line-addition {
  display: block;
  font-size: 0.8rem;
  color: var(--muted);
  margin-top: 0.15rem;
}
.err-text {
  color: var(--danger);
  margin-top: 0.5rem;
}
</style>
