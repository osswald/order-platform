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
import { useRoute, useRouter } from 'vue-router'
import PaymentTypePickerSheet from './components/PaymentTypePickerSheet.vue'
import TwintQrSheet from './components/TwintQrSheet.vue'
import { api, isAndroidApp } from './api'
import { applyAndroidSafeAreaInsets } from './utils/androidInsets'
import { useBundle } from './composables/useBundle'
import { useBundleRefresh } from './composables/useBundleRefresh'
import { useToast } from './composables/useToast'
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
const route = useRoute()
const router = useRouter()
const { toast } = useToast()
const { bundleReady, refreshBundle } = useBundle()

useBundleRefresh()

if (isAndroidApp()) {
  router.afterEach(() => {
    applyAndroidSafeAreaInsets()
    requestAnimationFrame(applyAndroidSafeAreaInsets)
  })
}

onMounted(() => {
  if (isAndroidApp()) {
    applyAndroidSafeAreaInsets()
    requestAnimationFrame(applyAndroidSafeAreaInsets)
  }
  api('/v1/setup/status')
    .then((status) => {
      if (!status?.configured && route.name !== 'setup') {
        router.replace({ name: 'setup' })
      }
    })
    .catch(() => {})
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

const fullscreen = computed(() => Boolean(route.meta.fullscreen))
</script>
