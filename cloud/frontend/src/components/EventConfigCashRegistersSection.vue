<template>
  <div class="event-config-cash-registers-section">
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addCashRegister">{{ $t('events.config.addCashRegister') }}</v-btn>
    </div>
    <div v-for="(reg, ri) in cashRegisters" :key="'reg-' + ri" class="config-card">
      <div class="config-card-header">
        <span>{{ reg.name || $t('events.config.unnamedCashRegister') }}</span>
        <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeCashRegister(ri)" />
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
        <div class="form-field">
          <label>{{ $t('events.config.pickupCodeLetters') }}</label>
          <v-text-field
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
          />
        </div>
      </div>
    </div>
    <p v-if="!cashRegisters.length" class="muted">{{ $t('events.config.noCashRegisters') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import { rules } from '../utils/formRules.js'
import type { EventCashRegisterLocal, LayoutOption } from '@/types/ui'
import type { PrinterOptionRead } from '@/types/api'

const props = withDefaults(
  defineProps<{
    layoutOptions?: LayoutOption[]
    defaultLayoutUuid?: string
    printerOptions?: PrinterOptionRead[]
    accountsEnabled?: boolean
  }>(),
  {
    layoutOptions: () => [],
    defaultLayoutUuid: '',
    printerOptions: () => [],
    accountsEnabled: false,
  },
)

const cashRegisters = defineModel<EventCashRegisterLocal[]>({ required: true })

const { t } = useI18n()

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
    subsidiary_code: '',
  })
}

function removeCashRegister(idx: number) {
  cashRegisters.value.splice(idx, 1)
}
</script>
