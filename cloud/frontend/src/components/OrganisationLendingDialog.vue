<template>
  <Dialog
    :visible="visible"
    header="Geräte ausleihen"
    modal
    class="org-lending-dialog"
    :style="{ width: '36rem' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="form-field">
      <label>Organisation</label>
      <p class="org-readonly">{{ organisationName || '—' }}</p>
    </div>
    <div class="field-row">
      <div class="form-field">
        <label>Startdatum</label>
        <DatePicker
          v-model="startDate"
          showIcon
          dateFormat="dd.mm.yy"
          placeholder="Startdatum"
        />
      </div>
      <div class="form-field">
        <label>Dauer (Tage)</label>
        <InputNumber v-model="durationDays" :min="1" :max="3650" showButtons />
      </div>
    </div>
    <div class="form-field">
      <label>Geräte</label>
      <MultiSelect
        v-model="selectedIds"
        :options="applianceOptionGroups"
        optionLabel="label"
        optionValue="value"
        optionGroupLabel="label"
        optionGroupChildren="items"
        optionDisabled="disabled"
        placeholder="Geräte wählen"
        display="chip"
        filter
        class="w-full"
        :loading="loadingAppliances"
        :disabled="!canPickAppliances"
      />
      <small v-if="loadingAppliances">Geräte werden geladen…</small>
      <small v-else-if="!canPickAppliances">Bitte Startdatum und Dauer angeben.</small>
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
    <template #footer>
      <Button label="Abbrechen" class="secondary-button" type="button" :disabled="submitting" @click="close" />
      <Button
        label="Ausleihen"
        class="primary-button"
        type="button"
        :disabled="!canSubmit || submitting"
        :loading="submitting"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import MultiSelect from 'primevue/multiselect'
import { apiFetch } from '../api'
import {
  applianceDisplayName,
  applianceTypeLabel,
  parseApiErrorDetail,
  toIsoDate,
} from '../applianceLending'

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

const startDate = ref(null)
const durationDays = ref(7)
const selectedIds = ref([])
const appliances = ref([])
const loadingAppliances = ref(false)
const submitting = ref(false)
const submitMessage = ref('')
const submitMessageType = ref('')
const submitFailures = ref([])

const canPickAppliances = computed(() => {
  if (!startDate.value) return false
  const d = durationDays.value
  return typeof d === 'number' && d >= 1
})

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

const blockedCount = computed(() => appliances.value.filter((a) => a.lendable === false).length)

const canSubmit = computed(() => {
  return (
    props.organisationId != null &&
    canPickAppliances.value &&
    selectedIds.value.length > 0 &&
    !loadingAppliances.value
  )
})

function resetForm() {
  startDate.value = new Date()
  durationDays.value = 7
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
    const duration = durationDays.value
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
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  submitMessage.value = ''
  submitMessageType.value = ''
  submitFailures.value = []

  const start = toIsoDate(startDate.value)
  const duration = durationDays.value
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

watch([startDate, durationDays], () => {
  if (props.visible && canPickAppliances.value) {
    fetchAppliances()
  } else if (!canPickAppliances.value) {
    appliances.value = []
    selectedIds.value = []
  }
})
</script>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

label {
  font-size: 0.875rem;
  font-weight: 600;
}

.org-readonly {
  margin: 0;
  font-size: 1rem;
}

.blocked-hint {
  color: var(--p-text-muted-color);
}

.failure-list {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: var(--p-red-500);
}

.success {
  color: var(--p-green-600);
}

.warn {
  color: var(--p-orange-600);
}

.error {
  color: var(--p-red-500);
}

.w-full {
  width: 100%;
}

:deep(.p-datepicker),
:deep(.p-inputnumber),
:deep(.p-multiselect) {
  width: 100%;
}
</style>
