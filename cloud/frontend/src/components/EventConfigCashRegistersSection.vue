<template>
  <div class="event-config-cash-registers-section">
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addCashRegister">{{ $t('events.config.addCashRegister') }}</v-btn>
    </div>
    <div class="pickup-prefix-mode-block">
      <div class="form-field">
        <label>{{ $t('events.config.pickupPrefixMode') }}</label>
        <v-select
          data-testid="pickup-prefix-mode"
          :model-value="pickupPrefixMode"
          :items="pickupPrefixModeOptions"
          item-title="label"
          item-value="value"
          density="compact"
          hide-details
          :disabled="pickupPrefixModeLocked"
          @update:model-value="onPickupPrefixModeChange"
        />
      </div>
      <small
        v-if="pickupPrefixModeLocked"
        data-testid="pickup-prefix-mode-locked-hint"
        class="toggle-hint"
      >
        {{ $t('events.config.pickupPrefixModeLockedHint') }}
      </small>
    </div>
    <div v-for="(reg, ri) in cashRegisters" :key="'reg-' + ri" class="config-card">
      <div class="config-card-header">
        <span>{{ reg.name || $t('events.config.unnamedCashRegister') }}</span>
        <v-btn icon="mdi-delete" color="error" type="button" @click="removeCashRegister(ri)" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
          <v-text-field
            v-model="reg.name"
            :placeholder="$t('events.config.cashRegisterPlaceholder')"
            density="compact"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
        <div v-if="pickupPrefixMode === 'register'" class="form-field">
          <label>{{ $t('events.config.pickupCodeLetters') }}</label>
          <v-text-field
            data-testid="register-pickup-prefix"
            :model-value="reg.pickup_code_prefix"
            maxlength="3"
            placeholder="A"
            density="compact"
            hide-details
            @update:model-value="(v) => { reg.pickup_code_prefix = normalizePickupPrefix(v) }"
          />
        </div>
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>{{ $t('events.config.pin') }}</label>
          <v-text-field v-model="reg.pin" maxlength="4" placeholder="0000" density="compact" hide-details />
        </div>
        <div v-if="accountsEnabled" class="form-field">
          <label>{{ $t('events.config.subsidiaryCode') }}</label>
          <v-text-field v-model="reg.subsidiary_code" maxlength="32" density="compact" hide-details />
        </div>
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>{{ $t('events.config.layout') }}</label>
          <v-select
            v-model="reg.layout_uuid"
            :items="layoutOptions"
            item-title="name"
            item-value="value"
            :placeholder="$t('events.config.selectLayout')"
            density="compact"
            hide-details
          />
        </div>
        <div class="form-field">
          <label>{{ $t('events.config.customerPrinter') }}</label>
          <v-select
            v-model="reg.receipt_printer_appliance_id"
            :items="printerOptions"
            item-title="name"
            item-value="id"
            :placeholder="$t('events.config.noPrinter')"
            clearable
            density="compact"
            hide-details
            @update:model-value="onReceiptPrinterChange(reg, $event)"
          />
        </div>
      </div>
      <div v-if="sumupReaderOptions.length" class="field-row">
        <div class="form-field">
          <label>{{ $t('events.config.sumupReader') }}</label>
          <v-select
            v-model="reg.sumup_reader_id"
            :items="sumupReaderOptions"
            item-title="label"
            item-value="sumup_reader_id"
            :placeholder="$t('events.config.noSumupReader')"
            clearable
            density="compact"
            hide-details
          />
        </div>
      </div>
      <div v-if="reg.receipt_printer_appliance_id" class="field-row">
        <div class="form-field">
          <label>{{ $t('events.config.cashDrawer') }}</label>
          <v-select
            v-model="reg.cash_drawer_command"
            :items="cashDrawerOptions"
            item-title="label"
            item-value="value"
            density="compact"
            hide-details
          />
        </div>
      </div>
    </div>
    <p v-if="!cashRegisters.length" class="muted">{{ $t('events.config.noCashRegisters') }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import { rules } from '../utils/formRules.js'
import type { EventCashRegisterLocal, LayoutOption, PickupPrefixMode } from '@/types/ui'
import type { PrinterOptionRead } from '@/types/api'

const props = withDefaults(
  defineProps<{
    layoutOptions?: LayoutOption[]
    defaultLayoutUuid?: string
    printerOptions?: PrinterOptionRead[]
    accountsEnabled?: boolean
    sumupReaderOptions?: Array<{ sumup_reader_id: string; label: string }>
    pickupPrefixMode?: PickupPrefixMode
    pickupPrefixModeLocked?: boolean
  }>(),
  {
    layoutOptions: () => [],
    defaultLayoutUuid: '',
    printerOptions: () => [],
    accountsEnabled: false,
    sumupReaderOptions: () => [],
    pickupPrefixMode: 'register',
    pickupPrefixModeLocked: false,
  },
)

const cashRegisters = defineModel<EventCashRegisterLocal[]>({ required: true })
const emit = defineEmits<{
  'update:pickupPrefixMode': [value: PickupPrefixMode]
}>()

const { t } = useI18n()

const pickupPrefixModeOptions = computed(() => [
  { value: 'register' as const, label: t('events.config.pickupPrefixModeRegister') },
  { value: 'station' as const, label: t('events.config.pickupPrefixModeStation') },
])

function onPickupPrefixModeChange(value: PickupPrefixMode) {
  if (props.pickupPrefixModeLocked) return
  emit('update:pickupPrefixMode', value === 'station' ? 'station' : 'register')
}

const cashDrawerOptions = computed(() => [
  { value: 'none', label: t('events.config.cashDrawerNone') },
  { value: 'escp_pin2', label: t('events.config.cashDrawerEscpPin2') },
  { value: 'escp_pin5', label: t('events.config.cashDrawerEscpPin5') },
  { value: 'escp_pin2_long', label: t('events.config.cashDrawerEscpPin2Long') },
  { value: 'escp_pin5_long', label: t('events.config.cashDrawerEscpPin5Long') },
])

function onReceiptPrinterChange(reg: EventCashRegisterLocal, value: number | null) {
  reg.receipt_printer_appliance_id = value
  if (!value) {
    reg.cash_drawer_command = 'none'
  }
}

function normalizePickupPrefix(value: string | null | undefined): string {
  return String(value || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3)
}

function addCashRegister() {
  cashRegisters.value.push({
    name: t('events.config.cashRegisterFallback', { n: cashRegisters.value.length + 1 }),
    pickup_code_prefix: String.fromCharCode(65 + (cashRegisters.value.length % 26)),
    pin: '0000',
    layout_uuid: props.defaultLayoutUuid || '',
    receipt_printer_appliance_id: null,
    cash_drawer_command: 'none',
    subsidiary_code: '',
    sumup_reader_id: null,
  })
}

function removeCashRegister(idx: number) {
  cashRegisters.value.splice(idx, 1)
}
</script>

<style scoped>
.pickup-prefix-mode-block {
  margin-bottom: 1rem;
}

.pickup-prefix-mode-block .toggle-hint {
  display: block;
  margin-top: 0.25rem;
  opacity: 0.75;
}
</style>
