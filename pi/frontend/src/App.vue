<template>
  <div class="app-shell" :class="{ 'app-shell--fullscreen': fullscreen }">
    <main class="app-main" :class="{ 'app-main--fullscreen': fullscreen }">
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
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBundleRefresh } from './composables/useBundleRefresh'
import PaymentTypePickerSheet from './components/PaymentTypePickerSheet.vue'
import TwintQrSheet from './components/TwintQrSheet.vue'
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
import * as store from './store'

useBundleRefresh()

onMounted(() => {
  if (!store.bundleReady()) {
    store.refreshBundle().catch(() => {})
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

const route = useRoute()
const toast = computed(() => store.toast.value)
const fullscreen = computed(() => Boolean(route.meta.fullscreen))
</script>
