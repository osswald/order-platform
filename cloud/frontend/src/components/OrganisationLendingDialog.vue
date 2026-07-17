<template>
  <v-dialog
    :model-value="visible"
    max-width="36rem"
    @update:model-value="$emit('update:visible', $event)"
  >
    <v-card class="org-lending-dialog">
      <v-card-title>{{ $t('lending.title') }}</v-card-title>
      <v-card-text>
        <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>
        <v-form ref="formRef" @submit.prevent="submit">
          <div class="form-field">
            <FormLabel>{{ $t('common.organisation') }}</FormLabel>
            <p class="org-readonly">{{ organisationName || $t('common.emDash') }}</p>
          </div>
          <div class="field-row">
            <div class="form-field">
              <FormLabel required>{{ $t('lending.startDate') }}</FormLabel>
              <v-menu v-model="startDateMenuOpen" :close-on-content-click="false">
                <template #activator="{ props: menuProps }">
                  <v-text-field
                    :model-value="startDateDisplay"
                    :placeholder="$t('lending.startDate')"
                    density="compact"
                    hide-details="auto"
                    readonly
                    prepend-inner-icon="mdi-calendar"
                    v-bind="menuProps"
                    :rules="[startDateRule]"
                  />
                </template>
                <v-date-picker
                  :model-value="startDate"
                  @update:model-value="onStartDatePick"
                />
              </v-menu>
            </div>
            <div class="form-field">
              <FormLabel required>{{ $t('lending.endDate') }}</FormLabel>
              <v-menu v-model="endDateMenuOpen" :close-on-content-click="false">
                <template #activator="{ props: menuProps }">
                  <v-text-field
                    :model-value="endDateDisplay"
                    :placeholder="$t('lending.endDate')"
                    density="compact"
                    hide-details="auto"
                    readonly
                    prepend-inner-icon="mdi-calendar"
                    v-bind="menuProps"
                    :rules="[endDateRequiredRule, endDateRangeRule]"
                  />
                </template>
                <v-date-picker
                  :model-value="endDate"
                  :min="startDate"
                  @update:model-value="onEndDatePick"
                />
              </v-menu>
            </div>
          </div>
          <small v-if="rangeHint" class="range-hint">{{ rangeHint }}</small>
          <div class="form-field">
            <FormLabel required>{{ $t('common.appliances') }}</FormLabel>
            <v-select
              v-model="selectedIds"
              :items="applianceSelectItems"
              item-title="title"
              item-value="value"
              :placeholder="$t('lending.selectAppliances')"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details="auto"
              required
              :rules="[rules.requiredArray]"
              :loading="loadingAppliances"
              :disabled="!canPickAppliances"
            >
              <template #item="{ item, props: itemProps }">
                <v-list-subheader v-if="item.type === 'subheader'">
                  <ApplianceTypeChip :type="item.applianceType" />
                </v-list-subheader>
                <v-list-item v-else v-bind="itemProps" />
              </template>
            </v-select>
            <small v-if="loadingAppliances">{{ $t('lending.loadingAppliances') }}</small>
            <small v-else-if="!canPickAppliances">{{ $t('lending.pickDatesFirst') }}</small>
            <small v-else-if="noAppliancesAvailable" class="muted-hint">
              {{ $t('lending.noAppliancesAvailable') }}
            </small>
          </div>
          <p v-if="submitMessage" :class="submitMessageType">{{ submitMessage }}</p>
          <ul v-if="submitFailures.length" class="failure-list">
            <li v-for="(f, i) in submitFailures" :key="i">
              {{ f.name }}: {{ f.detail }}
            </li>
          </ul>
        </v-form>
      </v-card-text>
      <v-card-actions class="dialog-actions">
        <v-spacer />
        <v-btn variant="outlined" :disabled="submitting" @click="close">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="submit"
        >
          {{ $t('common.lend') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FormLabel from './FormLabel.vue'
import ApplianceTypeChip from './ApplianceTypeChip.vue'
import { apiJson } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { currentLocale } from '../i18n'
import { collatorLocale } from '../utils/localeFormat'
import {
  applianceDisplayName,
  applianceTypeLabel,
  defaultLendingEndDate,
  formatDeDate,
  inclusiveDurationDays,
  isValidLendingRange,
  lendingRangeHint,
  toIsoDate,
  toLocalCalendarDate,
} from '../utils/applianceLending'
import type { ApplianceRead } from '@/types/api'
import { isApiError } from '@/types/api'
import type { LendingSubmitFailure } from '@/types/ui'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    visible?: boolean
    organisationId?: number | null
    organisationName?: string
  }>(),
  {
    visible: false,
    organisationId: null,
    organisationName: '',
  },
)

const emit = defineEmits<{
  'update:visible': [value: boolean]
  completed: []
}>()

const formRef = ref(null)
const startDate = ref<Date | null>(null)
const endDate = ref<Date | null>(null)
const startDateMenuOpen = ref(false)
const endDateMenuOpen = ref(false)
const selectedIds = ref<number[]>([])
const appliances = ref<ApplianceRead[]>([])
const loadingAppliances = ref(false)
const submitting = ref(false)
const submitMessage = ref('')
const submitMessageType = ref('')
const submitFailures = ref<LendingSubmitFailure[]>([])

const startDateDisplay = computed(() =>
  startDate.value ? formatDeDate(startDate.value) : '',
)
const endDateDisplay = computed(() => (endDate.value ? formatDeDate(endDate.value) : ''))

const startDateRule = () => rules.requiredDate(startDate.value)
const endDateRequiredRule = () => rules.requiredDate(endDate.value)
const endDateRangeRule = () =>
  isValidLendingRange(startDate.value, endDate.value) ||
  t('lending.endDateRangeError')

const canPickAppliances = computed(() => isValidLendingRange(startDate.value, endDate.value))

const rangeHint = computed(() => lendingRangeHint(startDate.value, endDate.value))

const applianceById = computed(() => {
  const map = new Map<number, ApplianceRead>()
  for (const a of appliances.value) {
    map.set(a.id, a)
  }
  return map
})

const lendableAppliances = computed(() =>
  appliances.value.filter((a) => a.lendable !== false),
)

const applianceOptionGroups = computed(() => {
  const locale = collatorLocale(currentLocale())
  const byType = new Map()
  for (const a of lendableAppliances.value) {
    const type = a.type || 'other'
    if (!byType.has(type)) byType.set(type, [])
    byType.get(type).push({
      label: applianceDisplayName(a),
      value: a.id,
    })
  }
  return [...byType.entries()]
    .sort(([a], [b]) => applianceTypeLabel(a).localeCompare(applianceTypeLabel(b), locale))
    .map(([type, items]) => ({
      type,
      label: applianceTypeLabel(type),
      items: items.sort((x: { label: string }, y: { label: string }) => x.label.localeCompare(y.label, locale)),
    }))
})

const applianceSelectItems = computed(() => {
  const items = []
  for (const group of applianceOptionGroups.value) {
    items.push({ type: 'subheader', title: group.label, applianceType: group.type })
    for (const item of group.items) {
      items.push({
        title: item.label,
        value: item.value,
      })
    }
  }
  return items
})

const noAppliancesAvailable = computed(
  () => canPickAppliances.value && !loadingAppliances.value && lendableAppliances.value.length === 0,
)

function onStartDatePick(value: Date | string | null) {
  startDate.value = toLocalCalendarDate(value)
  startDateMenuOpen.value = false
  if (startDate.value && endDate.value && !isValidLendingRange(startDate.value, endDate.value)) {
    endDate.value = defaultLendingEndDate(startDate.value)
  }
}

function onEndDatePick(value: Date | string | null) {
  endDate.value = toLocalCalendarDate(value)
  endDateMenuOpen.value = false
}

function resetForm() {
  const start = toLocalCalendarDate(new Date()) ?? new Date()
  startDate.value = start
  endDate.value = defaultLendingEndDate(start)
  startDateMenuOpen.value = false
  endDateMenuOpen.value = false
  selectedIds.value = []
  appliances.value = []
  submitMessage.value = ''
  submitMessageType.value = ''
  submitFailures.value = []
}

function close() {
  emit('update:visible', false)
}

async function fetchAppliances() {
  if (!canPickAppliances.value) {
    appliances.value = []
    return
  }
  loadingAppliances.value = true
  try {
    const start = toIsoDate(startDate.value)
    const duration = inclusiveDurationDays(startDate.value, endDate.value)
    if (start == null || duration == null) {
      appliances.value = []
      return
    }
    const params = new URLSearchParams({
      lend_check_start: start,
      lend_check_duration: String(duration),
    })
    appliances.value = await apiJson<ApplianceRead[]>(`/appliances/?${params}`)
    const allowed = new Set(appliances.value.filter((a) => a.lendable !== false).map((a) => a.id))
    selectedIds.value = selectedIds.value.filter((id) => allowed.has(id))
  } catch {
    appliances.value = []
    submitMessage.value = t('lending.loadAppliancesError')
    submitMessageType.value = 'error'
  } finally {
    loadingAppliances.value = false
  }
}

async function submit() {
  if (submitting.value) return
  if (props.organisationId == null) return
  if (!(await validateForm(formRef))) return
  submitting.value = true
  submitMessage.value = ''
  submitMessageType.value = ''
  submitFailures.value = []

  const start = toIsoDate(startDate.value)
  const duration = inclusiveDurationDays(startDate.value, endDate.value)
  const orgId = props.organisationId
  let ok = 0
  const failures: LendingSubmitFailure[] = []
  const failedIds: number[] = []

  for (const applianceId of selectedIds.value) {
    const appliance = applianceById.value.get(applianceId)
    const name = appliance ? applianceDisplayName(appliance) : `#${applianceId}`
    try {
      await apiJson(`/appliances/${applianceId}/lendings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organisation_id: orgId,
          start_date: start,
          duration_days: duration,
        }),
      })
      ok += 1
    } catch (err: unknown) {
      failures.push({
        name,
        detail: isApiError(err) ? err.message || t('lending.requestFailed') : t('lending.requestFailed'),
      })
      failedIds.push(applianceId)
    }
  }

  submitFailures.value = failures
  const total = selectedIds.value.length
  if (ok === total) {
    submitMessage.value = ok === 1
      ? t('lending.createdOne', { count: ok })
      : t('lending.createdMany', { count: ok })
    submitMessageType.value = 'success'
    emit('completed')
    close()
  } else if (ok > 0) {
    submitMessage.value = t('lending.partialSuccess', { ok, total })
    submitMessageType.value = 'warn'
    emit('completed')
    selectedIds.value = failedIds
    await fetchAppliances()
  } else {
    submitMessage.value = t('lending.createFailed')
    submitMessageType.value = 'error'
  }
  submitting.value = false
}

watch(
  () => props.visible,
  (open) => {
    if (open) {
      resetForm()
      if (canPickAppliances.value) fetchAppliances()
    }
  },
)

watch([startDate, endDate], () => {
  if (props.visible && canPickAppliances.value) {
    fetchAppliances()
  } else if (!canPickAppliances.value) {
    appliances.value = []
    selectedIds.value = []
  }
})
</script>

<style scoped>
.org-readonly {
  margin: 0;
  font-size: 1rem;
}

.range-hint {
  display: block;
  margin: 0 0 0.75rem;
  opacity: 0.75;
}

.muted-hint {
  opacity: 0.65;
}

.failure-list {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: rgb(var(--v-theme-error));
}
</style>
