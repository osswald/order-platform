<template>
  <SplitPaySettleScreen
    :header-title="headerTitle"
    empty-text="Keine offenen Posten."
    settled-toast="Bestellung bezahlt."
    :load-summary="loadSummary"
    :settle-partial-path="() => `/v1/orders/${orderId}/settle-partial`"
    actions-hide-transfer
    :actions-assign-path="`/v1/orders/${orderId}/assign-collective`"
    :receipt-target-uuid="registerUuid"
    :fixed-rows="fixedRows"
    :payment-hooks="paymentHooks"
    @back="onBack"
    @settled="onSettled"
    @load-error="goHub"
    @gone="onGone"
  />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import type { AccountSummaryResponse, RegisterDisplayPayload } from '@/types/api'
import type { PickPaymentHooks } from '@/utils/pickPaymentType'
import { cartLineLabelForEvent } from '@/utils/bundleHelpers'
import { useEventContext } from '@/composables/useEventContext'
import { useRegisterDisplay } from '@/composables/useRegisterDisplay'
import SplitPaySettleScreen, { type FixedSettleRow, type SettleResult } from '@/components/SplitPaySettleScreen.vue'

interface VoucherSaleSummaryLine {
  voucher_definition_uuid?: string | null
  name?: string
  qty?: number
  unit_cents?: number
  total_cents?: number
}

type OrderSummary = AccountSummaryResponse & {
  pickup_code?: string | null
  voucher_sale_lines?: VoucherSaleSummaryLine[]
  voucher_sale_cents?: number
}

const route = useRoute()
const router = useRouter()
const { event, showToast } = useEventContext()
const {
  register,
  registerUuid,
  pushDisplayPayload,
  setDisplayIdle,
  scheduleIdleAfterPickup,
  hubRoute,
} = useRegisterDisplay()

const orderId = computed(() => parseInt(String(route.params.orderId), 10))
const pickupCode = ref<string | null>(null)
const fixedRows = ref<FixedSettleRow[]>([])
const headerTitle = computed(() =>
  pickupCode.value ? `Bezahlen – Pickup ${pickupCode.value}` : 'Bezahlen',
)

const paymentHooks: PickPaymentHooks = {
  onTwintShow: ({ dataUrl, amountCents }) => {
    pushDisplayPayload({
      state: 'twint',
      show_twint: true,
      twint_qr_data_url: dataUrl,
      total_cents: amountCents ?? 0,
    })
  },
  onTwintHide: () => {},
}

async function loadSummary(): Promise<OrderSummary> {
  const data = await api<OrderSummary>(`/v1/orders/${orderId.value}/summary`)
  pickupCode.value = data.pickup_code || null
  fixedRows.value = (data.voucher_sale_lines || []).map((v, i) => ({
    key: `voucher-sale-${i}-${v.voucher_definition_uuid || ''}`,
    label: `Gutschein: ${v.name || 'Gutschein'}`,
    qty: Math.max(1, Number(v.qty) || 1),
    amountCents: Math.max(0, Number(v.total_cents) || 0),
  }))
  syncCustomerDisplay(data)
  return data
}

function syncCustomerDisplay(data: OrderSummary) {
  const lines = (data.open_orders || []).flatMap((o) =>
    (o.lines || []).map((l) => ({
      ...(l as Record<string, unknown>),
      display_label: cartLineLabelForEvent(l as never, event.value),
    })),
  ) as unknown as RegisterDisplayPayload['lines']
  pushDisplayPayload({
    state: 'ordering',
    show_twint: false,
    twint_qr_data_url: null,
    total_cents: data.total_cents || 0,
    voucher_lines: [],
    lines,
  } as Partial<RegisterDisplayPayload>)
}

function goHub() {
  router.push(hubRoute())
}

function onBack() {
  setDisplayIdle()
  if (pickupCode.value) {
    showToast(`Bestellung ${pickupCode.value} bleibt offen`, 'ok')
  }
  goHub()
}

function onGone() {
  setDisplayIdle()
  goHub()
}

async function onSettled(res: SettleResult) {
  void res
  scheduleIdleAfterPickup(10000)
  await pushDisplayPayload({
    state: 'submitted',
    pickup_code: pickupCode.value,
    pickup_status: null,
    lines: [],
    total_cents: 0,
    show_twint: false,
    twint_qr_data_url: null,
    voucher_lines: [],
  } as Partial<RegisterDisplayPayload>)
  if (pickupCode.value) showToast(`Pickup ${pickupCode.value}`, 'ok')
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  router.replace(hubRoute())
}
</script>
