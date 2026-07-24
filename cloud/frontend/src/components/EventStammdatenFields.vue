<template>
  <div class="event-stammdaten">
    <section class="field-group">
      <h3 class="field-group-title">{{ t('events.stammdaten.basis') }}</h3>
      <div class="form-field">
        <FormLabel required>{{ t('events.stammdaten.name') }}</FormLabel>
        <v-text-field
          v-model="form.name"
          :placeholder="t('events.stammdaten.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="field-row">
        <div class="form-field">
          <FormLabel required>{{ t('events.stammdaten.start') }}</FormLabel>
          <v-text-field
            :model-value="formatLocalDatetime(form.start)"
            type="datetime-local"
            :placeholder="t('events.stammdaten.startPlaceholder')"
            hide-details="auto"
            required
            :rules="[() => rules.requiredDate(form.start)]"
            @update:model-value="form.start = parseLocalDatetime($event)"
          />
        </div>
        <div class="form-field">
          <FormLabel required>{{ t('events.stammdaten.end') }}</FormLabel>
          <v-text-field
            :model-value="formatLocalDatetime(form.end)"
            type="datetime-local"
            :placeholder="t('events.stammdaten.endPlaceholder')"
            hide-details="auto"
            required
            :rules="[() => rules.requiredDate(form.end)]"
            @update:model-value="form.end = parseLocalDatetime($event)"
          />
        </div>
      </div>
    </section>

    <section class="field-group">
      <h3 class="field-group-title">{{ t('events.stammdaten.payment') }}</h3>
      <div class="form-field">
        <FormLabel>{{ t('events.stammdaten.paymentMode') }}</FormLabel>
        <v-select
          v-model="form.paymentMode"
          :items="paymentModeOptions"
          item-title="label"
          item-value="value"
          :placeholder="t('events.stammdaten.paymentModePlaceholder')"
          hide-details="auto"
        />
        <small>{{ t('events.stammdaten.paymentModeHint') }}</small>
      </div>
      <div v-if="isInstantMode" class="form-field">
        <FormLabel required>{{ t('events.stammdaten.instantCollectiveBill') }}</FormLabel>
        <v-text-field
          v-model="form.instantCollectiveBillName"
          :placeholder="t('events.stammdaten.instantCollectiveBillPlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
        <small>{{ t('events.stammdaten.instantCollectiveBillHint') }}</small>
      </div>
      <div v-if="!isInstantMode" class="form-field">
        <FormLabel required>{{ t('events.stammdaten.paymentTypes') }}</FormLabel>
        <v-select
          v-model="form.paymentTypes"
          :items="paymentTypeOptions"
          item-title="label"
          item-value="value"
          :placeholder="t('events.stammdaten.paymentTypesPlaceholder')"
          multiple
          chips
          closable-chips
          hide-details="auto"
          required
          :rules="[rules.requiredArray]"
        />
        <small>{{ t('events.stammdaten.paymentTypesHint') }}</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="offer-payment-receipt">{{ t('events.stammdaten.offerPaymentReceipt') }}</label>
          <v-switch
            id="offer-payment-receipt"
            v-model="form.offerPaymentReceipt"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">{{ t('events.stammdaten.offerPaymentReceiptHint') }}</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="bluetooth-printing-enabled">{{ t('events.stammdaten.bluetoothPrinting') }}</label>
          <v-switch
            id="bluetooth-printing-enabled"
            v-model="form.bluetoothPrintingEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">{{ t('events.stammdaten.bluetoothPrintingHint') }}</small>
      </div>
      <TwintQrField
        v-if="showTwintQrSection"
        :edit-mode="editMode"
        :active-id="activeId ?? undefined"
        :has-twint-qr="hasTwintQr"
        :preview-url="twintQrPreviewUrl"
        :preview-loading="twintQrPreviewLoading"
        :busy="twintQrBusy"
        @upload="$emit('upload', $event)"
        @remove="$emit('remove')"
      />
    </section>

    <section class="field-group">
      <h3 class="field-group-title">{{ t('events.stammdaten.config') }}</h3>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="cash-registers-enabled">{{ t('events.stammdaten.cashRegisters') }}</label>
          <v-switch
            id="cash-registers-enabled"
            v-model="form.cashRegistersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">{{ t('events.stammdaten.cashRegistersHint') }}</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="shift-settlement-enabled">{{ t('events.stammdaten.shiftSettlement') }}</label>
          <v-switch
            id="shift-settlement-enabled"
            v-model="form.shiftSettlementEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          {{ t('events.stammdaten.shiftSettlementHint') }}
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="vouchers-enabled">{{ t('events.stammdaten.vouchers') }}</label>
          <v-switch
            id="vouchers-enabled"
            v-model="form.vouchersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">{{ t('events.stammdaten.vouchersHintLine1') }}<br>
        {{ t('events.stammdaten.vouchersHintLine2') }}</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="alternative-printers-enabled">{{ t('events.stammdaten.alternativePrinters') }}</label>
          <v-switch
            id="alternative-printers-enabled"
            v-model="form.alternativePrintersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          {{ t('events.stammdaten.alternativePrintersHint') }}
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="kitchen-monitors-enabled">{{ t('events.stammdaten.kitchenMonitors') }}</label>
          <v-switch
            id="kitchen-monitors-enabled"
            v-model="form.kitchenMonitorsEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          {{ t('events.stammdaten.kitchenMonitorsHint') }}
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="discounts-enabled">{{ t('events.stammdaten.discounts') }}</label>
          <v-switch
            id="discounts-enabled"
            v-model="form.discountsEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          {{ t('events.stammdaten.discountsHintLine1') }}<br>
          {{ t('events.stammdaten.discountsHintLine2') }}
        </small>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import TwintQrField from './TwintQrField.vue'
import { rules } from '../utils/formRules.js'
import type { EventStammdatenForm, SelectOption } from '@/types/ui'

const { t } = useI18n()

const form = defineModel<EventStammdatenForm>('form', { required: true })

withDefaults(
  defineProps<{
    paymentModeOptions: SelectOption<string>[]
    paymentTypeOptions: SelectOption<string>[]
    showTwintQrSection?: boolean
    editMode?: boolean
    activeId?: number | null
    hasTwintQr?: boolean
    twintQrPreviewUrl?: string
    twintQrPreviewLoading?: boolean
    twintQrBusy?: boolean
  }>(),
  {
    showTwintQrSection: false,
    editMode: false,
    activeId: null,
    hasTwintQr: false,
    twintQrPreviewUrl: '',
    twintQrPreviewLoading: false,
    twintQrBusy: false,
  },
)

defineEmits<{
  upload: [file: File]
  remove: []
}>()

const isInstantMode = computed(() => (form.value.paymentMode || 'pay_later') === 'instant')

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

function formatLocalDatetime(value: Date | null | undefined): string {
  if (!value || !(value instanceof Date) || Number.isNaN(value.getTime())) {
    return ''
  }
  return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())}T${pad2(value.getHours())}:${pad2(value.getMinutes())}`
}

function parseLocalDatetime(value: string | null | undefined): Date | null {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}
</script>

<style scoped>
.field-group {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.field-group-title {
  margin: 0 0 0.65rem;
  font-size: 0.9375rem;
  font-weight: 600;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.toggle-block {
  margin-bottom: 0.65rem;
}

.toggle-block:last-child {
  margin-bottom: 0;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0;
}

.toggle-row label {
  font-size: 0.875rem;
  font-weight: 600;
}

.toggle-hint {
  display: block;
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  opacity: 0.7;
}

small {
  opacity: 0.7;
}

@media (max-width: 1000px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
