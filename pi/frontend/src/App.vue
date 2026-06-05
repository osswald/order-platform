<template>
  <div class="app-shell" :class="{ 'app-shell--fullscreen': fullscreen && !emulatedPrinter }">
    <div
      v-if="emulatedPrinter"
      class="hosted-demo-shell"
      :class="{ 'hosted-demo-shell--wide': isWide }"
    >
      <div class="hosted-demo-app">
        <main class="app-main" :class="{ 'app-main--fullscreen': fullscreen }">
          <RouterView />
        </main>
      </div>
      <aside v-if="isWide" class="hosted-demo-receipts">
        <EmulatedReceiptsPanel />
      </aside>
      <template v-else>
        <button type="button" class="hosted-demo-fab" @click="receiptsOpen = true">Belege</button>
        <ReceiptBottomSheet :open="receiptsOpen" @close="receiptsOpen = false">
          <EmulatedReceiptsPanel compact :show-header="false" />
        </ReceiptBottomSheet>
      </template>
    </div>
    <main v-else class="app-main" :class="{ 'app-main--fullscreen': fullscreen }">
      <RouterView />
    </main>

    <div class="toast-host" aria-live="polite">
      <div v-if="toast" class="toast" :class="toast.type">{{ toast.message }}</div>
    </div>
    <PaymentTypePickerSheet
      :open="paymentPickerOpen"
      :types="paymentPickerTypes"
      :amount-label="paymentPickerAmountLabel"
      @select="onPaymentTypeSelect"
      @cancel="onPaymentTypeCancel"
    />
    <TwintQrSheet
      :open="twintQrSheetOpen"
      :data-url="twintQrSheetDataUrl"
      :amount-label="twintQrSheetAmountLabel"
      @confirm="onTwintQrConfirm"
      @cancel="onTwintQrCancel"
    />
    <ShiftOpenDialog />
    <div v-if="terminalPaymentBusy" class="terminal-busy-overlay" aria-live="polite">
      <p>Karte an das Gerät halten…</p>
    </div>
    <PaymentReceiptPromptSheet
      :open="receiptPromptOpen"
      :step="receiptPromptStep"
      :targets="receiptPromptTargets"
      :busy="receiptPromptBusy"
      @yes="onReceiptPrintYes"
      @no="onReceiptPrintNo"
      @cancel="onReceiptPrintCancel"
      @select-station="onReceiptSelectStation"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ShiftOpenDialog from './components/ShiftOpenDialog.vue'
import PaymentTypePickerSheet from './components/PaymentTypePickerSheet.vue'
import PaymentReceiptPromptSheet from './components/PaymentReceiptPromptSheet.vue'
import TwintQrSheet from './components/TwintQrSheet.vue'
import EmulatedReceiptsPanel from './components/EmulatedReceiptsPanel.vue'
import ReceiptBottomSheet from './components/ReceiptBottomSheet.vue'
import { isAndroidApp } from './api'
import { applyAndroidSafeAreaInsets } from './utils/androidInsets'
import { useBundle } from './composables/useBundle'
import { useBundleRefresh } from './composables/useBundleRefresh'
import { useMediaQuery } from './composables/useMediaQuery'
import { useSetupStatus } from './composables/useSetupStatus'
import { useToast } from './composables/useToast'
import { useWaiterSession } from './composables/useWaiterSession'
import {
  startWaiterPrintFailurePolling,
  stopWaiterPrintFailurePolling,
} from './composables/useStationPrintFailures'
import {
  pickerOpen as paymentPickerOpen,
  pickerTypes as paymentPickerTypes,
  pickerAmountLabel as paymentPickerAmountLabel,
  twintQrOpen as twintQrSheetOpen,
  twintQrDataUrl as twintQrSheetDataUrl,
  twintQrAmountLabel as twintQrSheetAmountLabel,
  confirmPaymentType,
  cancelPaymentType,
  confirmTwintQr,
  cancelTwintQr,
} from './utils/pickPaymentType'
import { terminalPaymentBusy } from './utils/resolvePayment'
import {
  receiptPromptOpen,
  receiptPromptStep,
  receiptPromptTargets,
  receiptPromptBusy,
  confirmReceiptPrintYes,
  confirmReceiptPrintNo,
  cancelReceiptPrompt,
  selectReceiptStation,
} from './utils/paymentReceiptPrompt'

const route = useRoute()
const router = useRouter()
const { toast } = useToast()
const { bundleReady, refreshBundle } = useBundle()
const { waiter, selectedEventId } = useWaiterSession()
const { emulatedPrinter, fetchSetupStatus } = useSetupStatus()
const isWide = useMediaQuery('(min-width: 900px)')
const receiptsOpen = ref(false)

function syncHostedDemoBodyClass() {
  document.body.classList.toggle('hosted-pi-demo', Boolean(emulatedPrinter.value))
  document.body.classList.toggle(
    'hosted-pi-demo--wide',
    Boolean(emulatedPrinter.value && isWide.value),
  )
}

watch([emulatedPrinter, isWide], syncHostedDemoBodyClass, { immediate: true })

useBundleRefresh()

watch(
  [() => waiter.value?.uuid, selectedEventId],
  () => {
    stopWaiterPrintFailurePolling()
    const waiterUuid = waiter.value?.uuid
    const eventId = selectedEventId.value
    if (waiterUuid && eventId) {
      startWaiterPrintFailurePolling(() => ({
        eventId: selectedEventId.value,
        waiterUuid: waiter.value?.uuid,
      }))
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  stopWaiterPrintFailurePolling()
  document.body.classList.remove('hosted-pi-demo', 'hosted-pi-demo--wide')
})

if (isAndroidApp()) {
  router.afterEach(() => {
    applyAndroidSafeAreaInsets()
    requestAnimationFrame(applyAndroidSafeAreaInsets)
  })
}

onMounted(async () => {
  if (isAndroidApp()) {
    applyAndroidSafeAreaInsets()
    requestAnimationFrame(applyAndroidSafeAreaInsets)
  }
  const status = await fetchSetupStatus()
  if (!status?.configured && route.name !== 'setup') {
    router.replace({ name: 'setup' })
  }
  if (!bundleReady()) {
    refreshBundle().catch(() => {})
  }
})

function onPaymentTypeSelect(type) {
  confirmPaymentType(type)
}

function onPaymentTypeCancel() {
  cancelPaymentType()
}

function onTwintQrConfirm() {
  confirmTwintQr()
}

function onTwintQrCancel() {
  cancelTwintQr()
}

function onReceiptPrintYes() {
  confirmReceiptPrintYes()
}

function onReceiptPrintNo() {
  confirmReceiptPrintNo()
}

function onReceiptPrintCancel() {
  cancelReceiptPrompt()
}

function onReceiptSelectStation(uuid) {
  selectReceiptStation(uuid)
}

const fullscreen = computed(() => Boolean(route.meta.fullscreen))
</script>
