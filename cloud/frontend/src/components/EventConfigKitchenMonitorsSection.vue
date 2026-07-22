<template>
  <div class="event-config-kitchen-monitors-section">
    <div class="section-toolbar">
      <v-btn color="primary" type="button" @click="addKitchenMonitorPrinter">{{ $t('events.config.addPrinter') }}</v-btn>
    </div>
    <div
      v-for="(row, idx) in kitchenMonitors"
      :key="'km-' + idx"
      class="config-card"
    >
      <div class="config-card-header">
        <span>{{ kitchenMonitorLabel(row) }}</span>
        <v-btn
          icon="mdi-delete"
          color="error"
          type="button"
          :aria-label="$t('events.config.remove')"
          @click="removeKitchenMonitorPrinter(idx)"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('events.config.printer') }}</label>
        <v-select
          v-model="row.printer_appliance_id"
          :items="kitchenMonitorPrinterOptions"
          item-title="name"
          item-value="id"
          :placeholder="$t('events.config.selectPrinter')"
          density="compact"
          hide-details
        />
      </div>
      <div class="form-field">
        <label>{{ $t('events.config.displayNameOptional') }}</label>
        <v-text-field
          v-model="row.label"
          :placeholder="$t('events.config.displayNamePlaceholder')"
          density="compact"
          hide-details
        />
      </div>
    </div>
    <p v-if="!kitchenMonitors.length" class="muted">{{ $t('events.config.noKitchenMonitors') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { EventKitchenMonitorLocal } from '@/types/ui'
import type { PrinterOptionRead } from '@/types/api'

const props = withDefaults(
  defineProps<{
    printerOptions?: PrinterOptionRead[]
    kitchenMonitorPrinterOptions?: PrinterOptionRead[]
  }>(),
  {
    printerOptions: () => [],
    kitchenMonitorPrinterOptions: () => [],
  },
)

const kitchenMonitors = defineModel<EventKitchenMonitorLocal[]>({ required: true })

const { t } = useI18n()

function kitchenMonitorLabel(row: EventKitchenMonitorLocal): string {
  if ((row.label || '').trim()) return row.label.trim()
  const match = props.printerOptions.find(
    (opt) => Number(opt.id) === Number(row.printer_appliance_id),
  )
  return match?.name || t('events.config.printerFallback', { id: row.printer_appliance_id || '?' })
}

function addKitchenMonitorPrinter() {
  kitchenMonitors.value.push({
    printer_appliance_id: props.kitchenMonitorPrinterOptions[0]?.id ?? null,
    label: '',
  })
}

function removeKitchenMonitorPrinter(idx: number) {
  kitchenMonitors.value.splice(idx, 1)
}
</script>
