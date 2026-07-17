<template>
  <div class="split-pay-screen">
    <SplitPayHeader :table="headerTable" :title="headerTitle" @back="$emit('back')" @menu="onMenu">
      <template #actions>
        <button type="button" class="header-btn menu" aria-label="Menü" @click="onMenu">☰</button>
      </template>
    </SplitPayHeader>

    <p v-if="loading" class="muted state-msg">Laden…</p>
    <template v-else-if="!groups.length && !fixedRows.length">
      <div class="state-msg">
        <p>{{ emptyText }}</p>
        <slot name="empty-extra" />
        <button type="button" class="btn primary" @click="$emit('back')">Zurück</button>
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
            <li v-for="f in fixedRows" :key="f.key" class="split-line top voucher-line fixed-line">
              <span class="cell qty">{{ f.qty }}</span>
              <span class="cell name">
                <span class="name-text">{{ f.label }}</span>
              </span>
              <span class="cell price">{{ formatMoney(f.amountCents, currency) }}</span>
            </li>
            <SplitPayVoucherRow
              v-for="(v, vi) in voucherBasketLines"
              :key="v.key"
              :label="v.label"
              :amount-cents="v.appliedCents"
              :currency="currency"
              @remove="removeVoucherLine(vi)"
            />
          </ul>
          <p v-if="!topGroups.length && !voucherBasketLines.length && !fixedRows.length" class="muted empty-hint">
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
            :disabled="paying || (!rawBasketCents && !fixedCents)"
            @click="onPay"
          >
            Teilbetrag {{ formatMoney(basketCents, currency) }}
            <template v-if="voucherCreditCents">
              <span class="bar-sub">(−{{ formatMoney(voucherCreditCents, currency) }} Gutschein)</span>
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
        <span class="bar-main">Rest {{ formatMoney(restCents, currency) }} / {{ formatMoney(totalCents, currency) }}</span>
        <button type="button" class="bar-side cancel" aria-label="Abbrechen" @click="$emit('back')">✕</button>
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
      :event-id="eventId"
      :from-table="actionsFromTable"
      :voucher-only="actionsVoucherOnly"
      :hide-transfer="actionsHideTransfer"
      :assign-path="actionsAssignPath"
      :selections="selectionsPayload()"
      @close="actionsOpen = false"
      @done="onActionsDone"
      @redeem-voucher="openVoucherRedeem"
    />

    <VoucherRedeemSheet
      :open="voucherSheetOpen"
      :event="event"
      :gross-cents="rawBasketCents"
      :selections="selectionsPayload()"
      :line-groups="groups as unknown as LineGroupEntry[]"
      @close="voucherSheetOpen = false"
      @apply="onVoucherApply"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEventContext } from '@/composables/useEventContext'
import type { LineGroupEntry, TablePartialSettleResponse } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { formatMoney } from '@/utils/money'
import type { PickPaymentHooks } from '@/utils/pickPaymentType'
import { useSplitPay, type SplitPaySummary, type VoucherRedemptionSelection } from '@/composables/useSplitPay'
import SplitPayHeader from '@/components/SplitPayHeader.vue'
import SplitPayLineRow from '@/components/SplitPayLineRow.vue'
import SplitPayVoucherRow from '@/components/SplitPayVoucherRow.vue'
import { voucherDefinitionByUuid } from '@/utils/bundleHelpers'
import QtyInputModal from '@/components/QtyInputModal.vue'
import PayTableActionsSheet from '@/components/PayTableActionsSheet.vue'
import VoucherRedeemSheet from '@/components/VoucherRedeemSheet.vue'
import { offerPaymentReceipt } from '@/utils/paymentReceiptPrompt'

export interface FixedSettleRow {
  key: string
  label: string
  qty: number
  amountCents: number
}

export type SettleResult = SplitPaySummary & Pick<TablePartialSettleResponse, 'payment_id'>

interface VoucherApplyPayload {
  voucher_definition_uuid: string
  applied_cents: number
  article_id?: number
  note?: string
  qty?: number
  additions?: LineGroupEntry['additions']
}

const props = withDefaults(
  defineProps<{
    headerTable?: number | string
    headerTitle?: string
    emptyText: string
    settledToast: string
    loadSummary: () => Promise<SplitPaySummary>
    settlePartialPath: () => string
    actionsFromTable?: number | null
    actionsVoucherOnly?: boolean
    actionsHideTransfer?: boolean
    actionsAssignPath?: string | null
    receiptTargetUuid?: string
    voucherRowLabel?: (name: string) => string
    /** Always-due rows on top of selectable lines (e.g. voucher sales). */
    fixedRows?: FixedSettleRow[]
    paymentHooks?: PickPaymentHooks
  }>(),
  {
    headerTable: '',
    headerTitle: '',
    actionsFromTable: null,
    actionsVoucherOnly: false,
    actionsHideTransfer: false,
    actionsAssignPath: null,
    receiptTargetUuid: undefined,
    voucherRowLabel: undefined,
    fixedRows: () => [],
    paymentHooks: undefined,
  },
)

const emit = defineEmits<{
  back: []
  settled: [res: SettleResult]
  'load-error': [message: string]
  /** The account disappeared while acting on it (e.g. fully assigned to a collective bill). */
  gone: []
}>()

const actionsOpen = ref(false)
const voucherSheetOpen = ref(false)
const voucherRedemptions = ref<VoucherRedemptionSelection[]>([])
const { event, currency, showToast } = useEventContext()
const paymentMode = computed(() => (event.value?.payment_mode || 'pay_later').toLowerCase())
const eventId = computed(() => event.value?.id ?? 0)
const fixedCents = computed(() => props.fixedRows.reduce((s, f) => s + f.amountCents, 0))

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
  loadSummary: () => props.loadSummary(),
  settlePartialPath: () => props.settlePartialPath(),
  fixedCents,
  paymentHooks: props.paymentHooks,
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
    const name = String(vd?.name || 'Gutschein')
    return {
      key: `voucher-${index}-${r.voucher_definition_uuid}`,
      label: props.voucherRowLabel ? props.voucherRowLabel(name) : name,
      appliedCents: Math.max(0, Number(r.applied_cents) || 0),
    }
  }),
)

function removeVoucherLine(index: number) {
  voucherRedemptions.value = voucherRedemptions.value.filter((_, i) => i !== index)
}

function onVoucherApply(redemption: VoucherApplyPayload) {
  const next: VoucherRedemptionSelection = {
    voucher_definition_uuid: redemption.voucher_definition_uuid,
    article_id: redemption.article_id ?? 0,
    applied_cents: redemption.applied_cents,
    note: redemption.note,
    qty: redemption.qty,
    additions: redemption.additions as VoucherRedemptionSelection['additions'],
  }
  voucherRedemptions.value = [...voucherRedemptions.value, next]
  voucherSheetOpen.value = false
  showToast('Gutschein berücksichtigt', 'ok')
}

async function onActionsDone() {
  voucherRedemptions.value = []
  try {
    await reload()
  } catch {
    emit('gone')
  }
}

async function onPay() {
  try {
    const res = (await onGreenCheck()) as SettleResult | undefined
    if (!res) return
    const fullySettled = Number(res.remaining_cents || 0) <= 0
    if (res.payment_id && event.value) {
      await offerPaymentReceipt({
        paymentId: res.payment_id,
        event: event.value,
        showToast,
        preferredTargetUuid: props.receiptTargetUuid,
      })
    }
    if (fullySettled) {
      showToast(props.settledToast, 'ok')
      emit('settled', res)
    }
  } catch (e: unknown) {
    const message = getErrorMessage(e, '')
    if (message) showToast(message, 'err')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await reload()
  } catch (e: unknown) {
    const message = getErrorMessage(e, 'Laden fehlgeschlagen')
    showToast(message, 'err')
    emit('load-error', message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.bar-sub {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.9;
}
.fixed-line .cell.price {
  font-weight: 600;
}
</style>
