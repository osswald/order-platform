<template>
  <v-dialog
    :model-value="visible"
    max-width="36rem"
    @update:model-value="$emit('update:visible', $event)"
  >
    <v-card class="org-lending-dialog">
      <v-card-title>Geräte ausleihen</v-card-title>
      <v-card-text>
        <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>
        <v-form ref="formRef" @submit.prevent="submit">
          <div class="form-field">
            <FormLabel>Organisation</FormLabel>
            <p class="org-readonly">{{ organisationName || '—' }}</p>
          </div>
          <div class="field-row">
            <div class="form-field">
              <FormLabel required>Startdatum</FormLabel>
              <v-date-input
                v-model="startDate"
                placeholder="Startdatum"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.requiredDate]"
                prepend-icon=""
                prepend-inner-icon="mdi-calendar"
              />
            </div>
            <div class="form-field">
              <FormLabel required>Enddatum</FormLabel>
              <v-date-input
                v-model="endDate"
                placeholder="Enddatum"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.requiredDate, endDateRule]"
                prepend-icon=""
                prepend-inner-icon="mdi-calendar"
              />
            </div>
          </div>
          <small v-if="rangeHint" class="range-hint">{{ rangeHint }}</small>
          <div class="form-field">
            <FormLabel required>Geräte</FormLabel>
            <v-select
              v-model="selectedIds"
              :items="applianceSelectItems"
              item-title="title"
              item-value="value"
              placeholder="Geräte wählen"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details="auto"
              required
              :rules="[rules.requiredArray]"
              :loading="loadingAppliances"
              :disabled="!canPickAppliances"
            />
            <small v-if="loadingAppliances">Geräte werden geladen…</small>
            <small v-else-if="!canPickAppliances">Bitte Start- und Enddatum angeben.</small>
            <small v-else-if="blockedCount" class="blocked-hint">
              {{ blockedCount }} Gerät{{ blockedCount === 1 ? '' : 'e' }} im gewählten Zeitraum nicht verfügbar.
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
          Abbrechen
        </v-btn>
        <v-btn
          color="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="submit"
        >
          Ausleihen
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import FormLabel from './FormLabel.vue'
import { apiFetch } from '../api'
import { parseApiErrorDetail } from '../utils/apiError'
import { rules, validateForm } from '../utils/formRules.js'
import {
  applianceDisplayName,
  applianceTypeLabel,
  defaultLendingEndDate,
  inclusiveDurationDays,
  isValidLendingRange,
  lendingRangeHint,
  toIsoDate,
} from '../utils/applianceLending'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  organisationId: {
    type: Number,
    default: null,
  },
  organisationName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:visible', 'completed'])

const formRef = ref(null)
const startDate = ref(null)
const endDate = ref(null)
const selectedIds = ref([])
const appliances = ref([])
const loadingAppliances = ref(false)
const submitting = ref(false)
const submitMessage = ref('')
const submitMessageType = ref('')
const submitFailures = ref([])

const endDateRule = (value) =>
  isValidLendingRange(startDate.value, value) || 'Enddatum muss am oder nach dem Startdatum liegen'

const canPickAppliances = computed(() => isValidLendingRange(startDate.value, endDate.value))

const rangeHint = computed(() => lendingRangeHint(startDate.value, endDate.value))

const applianceById = computed(() => {
  const map = new Map()
  for (const a of appliances.value) {
    map.set(a.id, a)
  }
  return map
})

const applianceOptionGroups = computed(() => {
  const byType = new Map()
  for (const a of appliances.value) {
    const type = a.type || 'other'
    if (!byType.has(type)) byType.set(type, [])
    byType.get(type).push({
      label: applianceDisplayName(a),
      value: a.id,
      disabled: a.lendable === false,
      title: a.lend_block_reason || undefined,
    })
  }
  return [...byType.entries()]
    .sort(([a], [b]) => applianceTypeLabel(a).localeCompare(applianceTypeLabel(b), 'de'))
    .map(([type, items]) => ({
      label: applianceTypeLabel(type),
      items: items.sort((x, y) => x.label.localeCompare(y.label, 'de')),
    }))
})

const applianceSelectItems = computed(() => {
  const items = []
  for (const group of applianceOptionGroups.value) {
    items.push({ type: 'subheader', title: group.label })
    for (const item of group.items) {
      items.push({
        title: item.label,
        value: item.value,
        disabled: item.disabled,
      })
    }
  }
  return items
})

const blockedCount = computed(() => appliances.value.filter((a) => a.lendable === false).length)

function resetForm() {
  const start = new Date()
  startDate.value = start
  endDate.value = defaultLendingEndDate(start)
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
    const params = new URLSearchParams({
      lend_check_start: start,
      lend_check_duration: String(duration),
    })
    const response = await apiFetch(`/appliances/?${params}`)
    if (!response.ok) throw new Error(await response.text())
    appliances.value = await response.json()
    const allowed = new Set(appliances.value.filter((a) => a.lendable !== false).map((a) => a.id))
    selectedIds.value = selectedIds.value.filter((id) => allowed.has(id))
  } catch {
    appliances.value = []
    submitMessage.value = 'Geräte konnten nicht geladen werden.'
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
  const failures = []
  const failedIds = []

  for (const applianceId of selectedIds.value) {
    const appliance = applianceById.value.get(applianceId)
    const name = appliance ? applianceDisplayName(appliance) : `#${applianceId}`
    try {
      const response = await apiFetch(`/appliances/${applianceId}/lendings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organisation_id: orgId,
          start_date: start,
          duration_days: duration,
        }),
      })
      if (!response.ok) {
        failures.push({ name, detail: await parseApiErrorDetail(response) })
        failedIds.push(applianceId)
      } else {
        ok += 1
      }
    } catch {
      failures.push({ name, detail: 'Anfrage fehlgeschlagen' })
      failedIds.push(applianceId)
    }
  }

  submitFailures.value = failures
  const total = selectedIds.value.length
  if (ok === total) {
    submitMessage.value = `${ok} Ausleihe${ok === 1 ? '' : 'n'} angelegt.`
    submitMessageType.value = 'success'
    emit('completed')
    close()
  } else if (ok > 0) {
    submitMessage.value = `${ok} von ${total} Ausleihen angelegt.`
    submitMessageType.value = 'warn'
    emit('completed')
    selectedIds.value = failedIds
    await fetchAppliances()
  } else {
    submitMessage.value = 'Keine Ausleihe konnte angelegt werden.'
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

.blocked-hint {
  opacity: 0.65;
}

.failure-list {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: rgb(var(--v-theme-error));
}
</style>
