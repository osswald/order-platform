<template>
  <div>
    <h1>Belege</h1>
    <p class="muted">{{ event?.name }} · {{ waiter?.name }}</p>

    <div class="row">
      <button type="button" class="btn" :disabled="loading" @click="loadPayments">Aktualisieren</button>
      <RouterLink class="btn" :to="{ name: 'android-printer' }">Drucker</RouterLink>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="loading" class="muted">Laden…</p>
    <p v-else-if="!payments.length" class="muted">Noch keine Belege.</p>

    <div v-for="payment in payments" :key="payment.payment_id" class="card receipt-card">
      <div>
        <strong>{{ title(payment) }}</strong>
        <p class="muted">
          {{ formatMoney(payment.total_cents, currency) }}
          <template v-if="payment.paid_at"> · {{ formatDate(String(payment.paid_at)) }}</template>
        </p>
        <p class="muted small">
          {{ (payment.payment_types as string[] | undefined)?.join(', ') || 'Zahlung' }} · {{ payment.item_count }} Position(en)
        </p>
      </div>
      <button type="button" class="btn primary" :disabled="printingId === payment.payment_id" @click="reprint(payment)">
        Nachdrucken
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useEventContext } from '@/composables/useEventContext'
import { api } from '@/api'
import type { PaymentListItem, PaymentsListResponse } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { formatMoney } from '@/utils/money'
import { offerPaymentReceipt } from '@/utils/paymentReceiptPrompt'

const { event, currency, waiter, showToast } = useEventContext()
const payments = ref<PaymentListItem[]>([])
const loading = ref(false)
const error = ref('')
const printingId = ref<number | null>(null)

function title(payment: PaymentListItem) {
  if (payment.table_number) return `Tisch ${payment.table_number}`
  if (payment.collective_bill_name) return `Sammelrechnung ${payment.collective_bill_name}`
  if (payment.order_number) return `Bestellung #${payment.order_number}`
  return `Beleg #${payment.payment_id}`
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

async function loadPayments() {
  if (!event.value?.id) return
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ event_id: String(event.value.id) })
    if (waiter.value?.uuid) params.set('waiter_uuid', waiter.value.uuid)
    const data = await api<PaymentsListResponse>(`/v1/payments?${params.toString()}`)
    payments.value = data?.payments || []
  } catch (e: unknown) {
    error.value = getErrorMessage(e, 'Belege konnten nicht geladen werden.')
  } finally {
    loading.value = false
  }
}

async function reprint(payment: PaymentListItem) {
  printingId.value = payment.payment_id
  try {
    if (!event.value) return
    await offerPaymentReceipt({
      paymentId: payment.payment_id,
      event: event.value,
      showToast,
      reprint: true,
    })
  } finally {
    printingId.value = null
  }
}

onMounted(loadPayments)
</script>

<style scoped>
.receipt-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.small {
  font-size: 0.85rem;
}
.err {
  color: var(--danger);
}
</style>
