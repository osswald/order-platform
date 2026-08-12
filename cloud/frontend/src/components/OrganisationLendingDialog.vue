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
          <div class="form-field">
            <FormLabel required>{{ $t('lending.rentalChoice') }}</FormLabel>
            <v-btn-toggle
              v-model="rentalMode"
              mandatory
              density="compact"
              class="mb-3"
              data-testid="rental-mode-toggle"
            >
              <v-btn value="existing" data-testid="rental-mode-existing">{{ $t('lending.modeExisting') }}</v-btn>
              <v-btn value="create" data-testid="rental-mode-create">{{ $t('lending.modeCreate') }}</v-btn>
            </v-btn-toggle>
          </div>
          <div v-if="rentalMode === 'existing'" class="form-field">
            <FormLabel required>{{ $t('lending.chooseRental') }}</FormLabel>
            <v-select
              v-model="selectedRentalId"
              :items="rentalSelectItems"
              item-title="title"
              item-value="value"
              :placeholder="$t('lending.chooseRental')"
              density="compact"
              hide-details="auto"
              :loading="loadingRentals"
              :disabled="loadingRentals || !rentalSelectItems.length"
              data-testid="rental-pick"
              :rules="[rules.required]"
            />
            <small v-if="!loadingRentals && !rentalSelectItems.length" class="muted-hint">
              {{ $t('lending.noRentalsForOrg') }}
            </small>
          </div>
          <template v-if="rentalMode === 'create'">
          <div class="form-field">
            <FormLabel>{{ $t('rentals.labelOptional') }}</FormLabel>
            <v-text-field
              v-model="newRentalLabel"
              density="compact"
              hide-details="auto"
              data-testid="rental-new-label"
            />
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
          </template>
          <p v-else-if="selectedRental" class="range-hint">
            {{ selectedRental.display_name }} · {{ selectedRental.start_date }} – {{ selectedRental.end_date }}
          </p>
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
              data-testid="appliance-multi-pick"
            >
              <template #item="{ item, props: itemProps }">
                <v-list-subheader v-if="item.type === 'subheader'">
                  <ApplianceTypeChip :type="item.applianceType" />
                </v-list-subheader>
                <v-list-item v-else v-bind="itemProps" />
              </template>
            </v-select>
            <small v-if="loadingAppliances">{{ $t('lending.loadingAppliances') }}</small>
            <small v-else-if="!canPickAppliances">{{ $t('lending.pickRentalOrDatesFirst') }}</small>
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
import type { ApplianceRead, RentalRead } from '@/types/api'
import { isApiError } from '@/types/api'
import type { LendingSubmitFailure } from '@/types/ui'
import { sortRentalsNewestFirst } from '../utils/rentalLendingGroups'

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
const rentalMode = ref<'existing' | 'create'>('existing')
const selectedRentalId = ref<number | null>(null)
const orgRentals = ref<RentalRead[]>([])
const loadingRentals = ref(false)
const newRentalLabel = ref('')
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

const selectedRental = computed(() =>
  orgRentals.value.find((row) => row.id === selectedRentalId.value) ?? null,
)

const effectiveStartIso = computed(() => {
  if (rentalMode.value === 'existing') return selectedRental.value?.start_date ?? null
  return toIsoDate(startDate.value)
})

const effectiveEndIso = computed(() => {
  if (rentalMode.value === 'existing') return selectedRental.value?.end_date ?? null
  return toIsoDate(endDate.value)
})

const canPickAppliances = computed(() => {
  if (rentalMode.value === 'existing') return selectedRental.value != null
  return isValidLendingRange(startDate.value, endDate.value)
})

const rangeHint = computed(() => lendingRangeHint(startDate.value, endDate.value))

const rentalSelectItems = computed(() =>
  sortRentalsNewestFirst(orgRentals.value).map((row) => ({
    title: `${row.display_name} (${row.start_date} – ${row.end_date})`,
    value: row.id,
  })),
)

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
  rentalMode.value = 'existing'
  selectedRentalId.value = null
  orgRentals.value = []
  newRentalLabel.value = ''
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

async function fetchOrgRentals() {
  if (props.organisationId == null) {
    orgRentals.value = []
    return
  }
  loadingRentals.value = true
  try {
    orgRentals.value = await apiJson<RentalRead[]>(
      `/rentals/?organisation_id=${props.organisationId}`,
    )
    if (
      selectedRentalId.value != null &&
      !orgRentals.value.some((row) => row.id === selectedRentalId.value)
    ) {
      selectedRentalId.value = null
    }
  } catch {
    orgRentals.value = []
  } finally {
    loadingRentals.value = false
  }
}

async function fetchAppliances() {
  if (!canPickAppliances.value) {
    appliances.value = []
    return
  }
  loadingAppliances.value = true
  try {
    const start = effectiveStartIso.value
    const end = effectiveEndIso.value
    if (start == null || end == null) {
      appliances.value = []
      return
    }
    const startDateObj = toLocalCalendarDate(start)
    const endDateObj = toLocalCalendarDate(end)
    const duration = inclusiveDurationDays(startDateObj, endDateObj)
    if (duration == null) {
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
  if (rentalMode.value === 'existing' && selectedRentalId.value == null) return
  if (rentalMode.value === 'create' && !isValidLendingRange(startDate.value, endDate.value)) return
  submitting.value = true
  submitMessage.value = ''
  submitMessageType.value = ''
  submitFailures.value = []

  const orgId = props.organisationId

  try {
    if (rentalMode.value === 'existing' && selectedRentalId.value != null) {
      for (const applianceId of selectedIds.value) {
        await apiJson(`/rentals/${selectedRentalId.value}/appliances`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ appliance_id: applianceId }),
        })
      }
    } else {
      const start = toIsoDate(startDate.value)
      const end = toIsoDate(endDate.value)
      if (!start || !end) {
        submitting.value = false
        return
      }
      await apiJson('/rentals/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organisation_id: orgId,
          start_date: start,
          end_date: end,
          label: newRentalLabel.value.trim() || null,
          appliance_ids: selectedIds.value,
        }),
      })
    }
    const count = selectedIds.value.length
    submitMessage.value = count === 1
      ? t('lending.createdOne', { count })
      : t('lending.createdMany', { count })
    submitMessageType.value = 'success'
    emit('completed')
    close()
  } catch (err: unknown) {
    submitMessage.value = isApiError(err) ? err.message || t('lending.createFailed') : t('lending.createFailed')
    submitMessageType.value = 'error'
  }
  submitting.value = false
}

watch(
  () => props.visible,
  (open) => {
    if (open) {
      resetForm()
      void fetchOrgRentals()
    }
  },
  { immediate: true },
)

watch([rentalMode, selectedRentalId, startDate, endDate], () => {
  if (!props.visible) return
  if (canPickAppliances.value) void fetchAppliances()
  else {
    appliances.value = []
    selectedIds.value = []
  }
})

watch(rentalMode, (mode) => {
  if (mode === 'existing') void fetchOrgRentals()
})

defineExpose({
  rentalMode,
  selectedRentalId,
  selectedIds,
  submit,
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
