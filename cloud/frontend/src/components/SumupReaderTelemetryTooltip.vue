<template>
  <v-tooltip location="top" open-delay="200">
    <template #activator="{ props: tipProps }">
      <span
        v-bind="tipProps"
        class="reader-label"
        data-testid="sumup-reader-label"
        @mouseenter="loadTelemetry"
      >
        {{ reader.label }}
      </span>
    </template>
    <div class="reader-telemetry" data-testid="sumup-reader-telemetry">
      <div v-if="serialLine">{{ serialLine }}</div>
      <div v-if="modelLine">{{ modelLine }}</div>
      <template v-if="telemetry?.telemetry_available">
        <div v-if="onlineLine">{{ onlineLine }}</div>
        <div v-if="batteryLine">{{ batteryLine }}</div>
        <div v-if="connectionLine">{{ connectionLine }}</div>
        <div v-if="firmwareLine">{{ firmwareLine }}</div>
        <div v-if="activityLine">{{ activityLine }}</div>
        <div v-if="stateLine">{{ stateLine }}</div>
      </template>
      <div v-else-if="loaded" class="reader-telemetry-unavailable">
        {{ $t('sumupDevices.telemetryUnavailable') }}
      </div>
      <div v-else>{{ $t('sumupDevices.telemetryLoading') }}</div>
    </div>
  </v-tooltip>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { currentLocale } from '../i18n'
import { formatDateTime } from '../utils/localeFormat'
import {
  fetchSumupReaderTelemetry,
  type SumupReader,
  type SumupReaderTelemetry,
} from '../utils/sumupCloud'

const props = defineProps<{
  organisationId: number
  reader: SumupReader
}>()

const { t } = useI18n()
const telemetry = ref<SumupReaderTelemetry | null>(null)
const loaded = ref(false)
let requested = false

const identityTelemetry = computed((): SumupReaderTelemetry => ({
  id: props.reader.id,
  sumup_reader_id: props.reader.sumup_reader_id,
  label: props.reader.label,
  device_identifier: props.reader.device_identifier ?? null,
  device_model: props.reader.device_model ?? null,
  telemetry_available: false,
  online_status: null,
  battery_level: null,
  connection_type: null,
  firmware_version: null,
  last_activity: null,
  state: null,
}))

const display = computed(() => telemetry.value ?? identityTelemetry.value)

const serialLine = computed(() => {
  const serial = display.value.device_identifier
  return serial ? `${t('sumupDevices.telemetrySerial')}: ${serial}` : ''
})
const modelLine = computed(() => {
  const model = display.value.device_model
  return model ? `${t('sumupDevices.telemetryModel')}: ${model}` : ''
})
const onlineLine = computed(() => {
  const status = display.value.online_status
  if (!status) return ''
  const key = `sumupDevices.telemetryOnlineStatus.${status}`
  const translated = t(key)
  const label = translated === key ? status : translated
  return `${t('sumupDevices.telemetryOnline')}: ${label}`
})
const batteryLine = computed(() => {
  const level = display.value.battery_level
  return typeof level === 'number' ? `${t('sumupDevices.telemetryBattery')}: ${level}%` : ''
})
const connectionLine = computed(() => {
  const connection = display.value.connection_type
  return connection ? `${t('sumupDevices.telemetryConnection')}: ${connection}` : ''
})
const firmwareLine = computed(() => {
  const firmware = display.value.firmware_version
  return firmware ? `${t('sumupDevices.telemetryFirmware')}: ${firmware}` : ''
})
const activityLine = computed(() => {
  const activity = display.value.last_activity
  if (!activity) return ''
  return `${t('sumupDevices.telemetryLastActivity')}: ${formatDateTime(activity, currentLocale())}`
})
const stateLine = computed(() => {
  const state = display.value.state
  return state ? `${t('sumupDevices.telemetryState')}: ${state}` : ''
})

async function loadTelemetry(): Promise<void> {
  if (requested) return
  requested = true
  try {
    telemetry.value = await fetchSumupReaderTelemetry(props.organisationId, props.reader.id)
  } catch {
    telemetry.value = identityTelemetry.value
  } finally {
    loaded.value = true
  }
}
</script>

<style scoped>
.reader-label {
  cursor: default;
  text-decoration: underline dotted;
  text-underline-offset: 0.2em;
}

.reader-telemetry {
  font-size: 0.85rem;
  line-height: 1.4;
}

.reader-telemetry-unavailable {
  opacity: 0.85;
}
</style>
