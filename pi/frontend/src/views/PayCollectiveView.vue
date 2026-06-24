<template>
  <div class="split-pay-screen">
    <SplitPayHeader :title="headerTitle" @back="router.push({ name: 'collective-open' })" @menu="onMenu" />

    <p v-if="loading" class="muted state-msg">Laden…</p>
    <template v-else-if="!groups.length">
      <div class="state-msg">
        <p>Noch keine Posten.</p>
        <p v-if="billName" class="muted empty-assign-hint">
          Am Tisch ☰ → Sammelrechnung → «{{ billName }}» Positionen zuordnen.
        </p>
        <button type="button" class="btn primary" @click="router.push({ name: 'collective-open' })">Zurück</button>
      </div>
    </template>
    <template v-else>
      <div class="split-body">
        <section class="panel top-panel">
          <ul class="line-list">
            <SplitPayLineRow
              v-for="g in topGroups"
              :key="g.key"
              variant="top"
              :name="g.name"
              :addition-labels="g.additionLabels"
              :basket-qty="g.basketQty"
              :total-qty="g.totalQty"
              :unit-cents="g.unitCents"
              :line-total-cents="g.lineTotalCents"
              :discount="g.discount"
              :note="g.note || ''"
              :articles="event?.articles || {}"
              :event="event"
              @tap-qty="openQtyModal(g)"
              @tap-name="bumpBasket(g, 1)"
              @tap-price="bumpBasket(g, -1)"
            />
            <SplitPayVoucherRow
              v-for="(v, vi) in voucherBasketLines"
              :key="v.key"
              :label="v.label"
              :amount-cents="v.appliedCents"
              @remove="removeVoucherLine(vi)"
            />
          </ul>
          <p v-if="!topGroups.length && !voucherBasketLines.length" class="muted empty-hint">
            Unten „↑“ oder Zeilen antippen für Teilzahlung
          </p>
        </section>

        <div class="bar bar-green">
          <button
            type="button"
            class="bar-side"
            :disabled="!basketItemCount"
            aria-label="Alle Positionen nach unten"
            @click="moveAllToBottom"
          >
            {{ basketItemCount }} ↓
          </button>
          <button
            type="button"
            class="bar-main"
            :disabled="paying || !rawBasketCents"
            @click="onPay"
          >
            Teilbetrag {{ formatAmount(basketCents) }}
            <template v-if="voucherCreditCents">
              <span class="bar-sub">(−{{ formatAmount(voucherCreditCents) }} Gutschein)</span>
            </template>
            <span class="check" aria-hidden="true">✓</span>
          </button>
        </div>

        <section class="panel bottom-panel">
          <ul class="line-list">
            <SplitPayLineRow
              v-for="g in bottomGroups"
              :key="g.key"
              variant="bottom"
              :name="g.name"
              :addition-labels="g.additionLabels"
              :basket-qty="g.basketQty"
              :total-qty="g.totalQty"
              :unit-cents="g.unitCents"
              :line-total-cents="g.lineTotalCents"
              :discount="g.discount"
              :note="g.note || ''"
              :articles="event?.articles || {}"
              :event="event"
              @tap-row="bumpBasket(g, 1)"
            />
          </ul>
        </section>
      </div>

      <div class="bar bar-red">
        <button
          type="button"
          class="bar-side"
          :disabled="!remainingItemCount"
          aria-label="Alle Positionen nach oben"
          @click="moveAllToTop"
        >
          {{ remainingItemCount }} ↑
        </button>
        <span class="bar-main">Rest {{ formatAmount(restCents) }} / {{ formatAmount(totalCents) }}</span>
        <button
          type="button"
          class="bar-side cancel"
          aria-label="Abbrechen"
          @click="router.push({ name: 'collective-open' })"
        >
          ✕
        </button>
      </div>
    </template>

    <QtyInputModal
      :open="qtyModalOpen"
      :name="qtyModalGroup?.name || ''"
      :max="qtyModalGroup?.totalQty || 0"
      :model-value="qtyModalGroup?.basketQty || 0"
      @close="qtyModalOpen = false"
      @confirm="onQtyConfirm"
    />

    <PayTableActionsSheet
      :open="actionsOpen"
      :event-id="event?.id"
      voucher-only
      :selections="selectionsPayload()"
      @close="actionsOpen = false"
      @redeem-voucher="openVoucherRedeem"
    />

    <VoucherRedeemSheet
      :open="voucherSheetOpen"
      :event="event"
      :gross-cents="rawBasketCents"
      :selections="selectionsPayload()"
      :line-groups="groups"
      @close="voucherSheetOpen = false"
      @apply="onVoucherApply"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventContext } from '../composables/useEventContext'
import { api } from '../api'
import { formatAmount } from '../utils/money'
import { useSplitPay } from '../composables/useSplitPay'
import SplitPayHeader from '../components/SplitPayHeader.vue'
import SplitPayLineRow from '../components/SplitPayLineRow.vue'
import SplitPayVoucherRow from '../components/SplitPayVoucherRow.vue'
import QtyInputModal from '../components/QtyInputModal.vue'
import PayTableActionsSheet from '../components/PayTableActionsSheet.vue'
import VoucherRedeemSheet from '../components/VoucherRedeemSheet.vue'
import { voucherDefinitionByUuid } from '../utils/bundleHelpers'
import { offerPaymentReceipt } from '../utils/paymentReceiptPrompt'

const route = useRoute()
const router = useRouter()
const billName = ref('')
const actionsOpen = ref(false)
const voucherSheetOpen = ref(false)
const voucherRedemptions = ref([])
const billId = computed(() => parseInt(String(route.query.id), 10))
const { event, showToast } = useEventContext()
const paymentMode = computed(() => (event.value?.payment_mode || 'pay_later').toLowerCase())
const headerTitle = computed(() =>
  billName.value ? `Sammelrechnung: ${billName.value}` : 'Sammelrechnung',
)

const {
  groups,
  loading,
  paying,
  qtyModalOpen,
  qtyModalGroup,
  totalCents,
  basketCents,
  restCents,
  basketItemCount,
  remainingItemCount,
  topGroups,
  bottomGroups,
  moveAllToBottom,
  moveAllToTop,
  bumpBasket,
  openQtyModal,
  onQtyConfirm,
  selectionsPayload,
  reload,
  onGreenCheck,
  rawBasketCents,
  voucherCreditCents,
} = useSplitPay({
  event,
  paymentMode,
  voucherRedemptions,
  loadSummary: async () => {
    const ev = event.value
    if (!ev || !billId.value) return { line_groups: [] }
    const data = await api(`/v1/collective-bills/${billId.value}?event_id=${ev.id}`)
    billName.value = data.name || ''
    return data
  },
  settlePartialPath: () => `/v1/collective-bills/${billId.value}/settle-partial`,
})

function onMenu() {
  actionsOpen.value = true
}

function openVoucherRedeem() {
  actionsOpen.value = false
  if (!rawBasketCents.value) {
    showToast('Zuerst Positionen für Teilzahlung auswählen', 'err')
    return
  }
  voucherSheetOpen.value = true
}

const voucherBasketLines = computed(() =>
  voucherRedemptions.value.map((r, index) => {
    const vd = voucherDefinitionByUuid(event.value, r.voucher_definition_uuid)
    const name = vd?.name || 'Gutschein'
    return {
      key: `voucher-${index}-${r.voucher_definition_uuid}`,
      label: `${name}`,
      appliedCents: Math.max(0, Number(r.applied_cents) || 0),
    }
  }),
)

function removeVoucherLine(index) {
  voucherRedemptions.value = voucherRedemptions.value.filter((_, i) => i !== index)
}

function onVoucherApply(redemption) {
  voucherRedemptions.value = [...voucherRedemptions.value, redemption]
  voucherSheetOpen.value = false
  showToast('Gutschein berücksichtigt', 'ok')
}

async function onPay() {
  try {
    const res = await onGreenCheck()
    if (!res) return
    const fullySettled = Number(res.remaining_cents || 0) <= 0
    if (res.payment_id) {
      await offerPaymentReceipt({
        paymentId: res.payment_id,
        event: event.value,
        showToast,
      })
    }
    if (fullySettled) {
      showToast('Sammelrechnung vollständig abgerechnet.', 'ok')
      router.replace({ name: 'collective-open' })
    }
  } catch (e) {
    if (e?.message) showToast(e.message, 'err')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await reload()
  } catch (e) {
    showToast(e.message || 'Laden fehlgeschlagen', 'err')
    router.replace({ name: 'collective-open' })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.empty-assign-hint {
  margin: 0.75rem 0 1rem;
  font-size: 0.95rem;
  line-height: 1.4;
  max-width: 22rem;
}
.bar-sub {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.9;
}
</style>
