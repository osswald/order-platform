<template>
  <div class="receipt-printing-section">
    <h3>{{ displayTitle }}</h3>
    <p v-if="displayHint" class="muted hint">{{ displayHint }}</p>
    <p v-if="!entityId" class="muted">{{ $t('receipts.saveFirst') }}</p>
    <p v-else-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else>
      <div class="form-field logo-field">
        <label>{{ $t('receipts.logoLabel') }}</label>
        <div v-if="logoPreviewUrl" class="logo-preview">
          <img :src="logoPreviewUrl" :alt="$t('receipts.logoAlt')" />
        </div>
        <input
          ref="fileInput"
          type="file"
          class="logo-file-input"
          accept="image/png,image/jpeg,.png,.jpg,.jpeg"
          @change="onLogoFile"
        />
        <div class="logo-actions">
          <v-btn
            type="button"
            variant="outlined"
            :disabled="logoBusy"
            @click="fileInput?.click()"
          >
            {{ $t('receipts.uploadLogo') }}
          </v-btn>
          <v-btn
            v-if="hasReceiptLogo || logoPreviewUrl"
            type="button"
            color="error"
            variant="outlined"
            :disabled="logoBusy"
            @click="removeLogo"
          >
            {{ $t('receipts.removeLogo') }}
          </v-btn>
        </div>
        <small>{{ $t('receipts.logoHint') }}</small>
      </div>

      <div v-if="isEvent" class="form-field">
        <label>{{ $t('receipts.eventTitleLabel') }}</label>
        <v-text-field
          v-model="config.label_event_title"
          :placeholder="$t('receipts.eventTitlePlaceholder')"
          density="compact"
          hide-details
        />
        <small>{{ $t('receipts.eventTitleHint') }}</small>
      </div>

      <v-tabs v-model="receiptTab" density="comfortable" class="receipt-tabs">
        <v-tab value="station">{{ $t('receipts.tabStation') }}</v-tab>
        <v-tab value="customer">{{ $t('receipts.tabCustomer') }}</v-tab>
        <v-tab value="payment">{{ $t('receipts.tabPayment') }}</v-tab>
      </v-tabs>
      <v-window v-model="receiptTab" class="receipt-tab-panels">
        <v-window-item value="station">
          <ReceiptProfileFields
            v-model="config.station_receipt"
            :pickup-label="$t('receipts.tablePickup')"
            :show-price-option="false"
          />
        </v-window-item>
        <v-window-item value="customer">
          <ReceiptProfileFields v-model="config.customer_receipt" :pickup-label="$t('receipts.pickupCode')" />
        </v-window-item>
        <v-window-item value="payment">
          <PaymentReceiptProfileFields v-model="config.payment_receipt" />
        </v-window-item>
      </v-window>

      <div v-if="!autosave" class="actions">
        <v-btn color="primary" type="button" :disabled="saving" @click="save">
          {{ $t('receipts.saveSettings') }}
        </v-btn>
      </div>
      <p v-if="saveMessage" class="muted" :class="{ 'error-text': saveMessage && !autosave }">{{ saveMessage }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, toRef, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import PaymentReceiptProfileFields from './PaymentReceiptProfileFields.vue'
import ReceiptProfileFields from './ReceiptProfileFields.vue'
import { useReceiptPrinting } from '../composables/useReceiptPrinting'

const { t } = useI18n()

const props = defineProps({
  apiBasePath: { type: String, default: '' },
  entityId: { type: [Number, String], default: null },
  isEvent: { type: Boolean, default: false },
  title: { type: String, default: '' },
  hint: { type: String, default: '' },
})

const emit = defineEmits(['status-change'])

const displayTitle = computed(() => props.title || t('receipts.title'))
const displayHint = computed(() => props.hint)

const autosave = computed(() => props.isEvent)

const fileInput = ref<HTMLInputElement | null>(null)
const receiptTab = ref('station')
const apiBasePathRef = toRef(props, 'apiBasePath')

const {
  loading,
  saving,
  logoBusy,
  loadError,
  saveMessage,
  hasReceiptLogo,
  logoPreviewUrl,
  config,
  load,
  save,
  uploadLogo,
  removeLogo,
  autosaveStatus,
  autosaveError,
  flushAutosave,
} = useReceiptPrinting(apiBasePathRef, { isEvent: props.isEvent, autosave: props.isEvent })

watch([autosaveStatus, autosaveError], () => {
  if (!props.isEvent) return
  emit('status-change', {
    status: autosaveStatus?.value ?? 'idle',
    errorMessage: autosaveError?.value ?? '',
  })
}, { immediate: true })

defineExpose({
  autosaveStatus,
  autosaveError,
  flushAutosave,
})

watch(
  () => [props.apiBasePath, props.entityId],
  ([path, id]) => {
    if (path && id) load()
  },
  { immediate: true },
)

function onLogoFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) uploadLogo(file)
  input.value = ''
}
</script>

<style scoped>
.receipt-printing-section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.hint {
  margin-bottom: 0.75rem;
}

.logo-preview {
  display: flex;
  justify-content: center;
  padding: 0.75rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}

.logo-preview img {
  max-width: 220px;
  max-height: 120px;
  object-fit: contain;
}

.logo-file-input {
  display: none;
}

.logo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.receipt-tabs {
  margin-top: 0.5rem;
}

.receipt-tab-panels {
  padding-top: 0.5rem;
}

.error-text {
  color: rgb(var(--v-theme-error));
  margin-top: 0.5rem;
}
</style>
