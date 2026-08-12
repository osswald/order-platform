<template>
  <div class="rentals-calendar">
    <div class="rentals-header">
      <div>
        <h1>{{ $t('rentals.title') }}</h1>
        <p class="muted">{{ $t('rentals.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <HelpLink slug="rental-calendar" variant="icon" />
        <v-btn color="primary" @click="openCreate()">{{ $t('rentals.create') }}</v-btn>
      </div>
    </div>

    <div class="toolbar">
      <v-btn-toggle v-model="view" mandatory density="compact" variant="outlined">
        <v-btn value="month" data-testid="view-month">{{ $t('rentals.month') }}</v-btn>
        <v-btn value="year" data-testid="view-year">{{ $t('rentals.year') }}</v-btn>
        <v-btn value="fleet" data-testid="view-fleet">{{ $t('rentals.fleet') }}</v-btn>
      </v-btn-toggle>
      <div class="nav-period">
        <v-btn icon="mdi-chevron-left" :aria-label="$t('rentals.prev')" @click="shift(-1)" />
        <strong>{{ periodLabel }}</strong>
        <v-btn icon="mdi-chevron-right" :aria-label="$t('rentals.next')" @click="shift(1)" />
        <v-btn variant="outlined" size="small" @click="goToday">{{ $t('rentals.today') }}</v-btn>
      </div>
    </div>

    <p v-if="message" :class="messageType">{{ message }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>

    <div v-else-if="view === 'month'" class="month-grid">
      <div v-for="wd in weekdayLabels" :key="wd" class="weekday">{{ wd }}</div>
      <button
        v-for="cell in monthCells"
        :key="cell.iso"
        type="button"
        class="day-cell"
        :class="{ 'day-cell--outside': !cell.inMonth }"
        @click="openCreate(cell.iso)"
      >
        <span class="day-num">{{ cell.date.getDate() }}</span>
        <button
          v-for="bar in barsOnDay(cell.iso)"
          :key="bar.id"
          type="button"
          class="rental-chip"
          :class="{ 'rental-chip--empty': !bar.filled }"
          :style="{ background: organisationBarColor(bar.organisationId) }"
          @click.stop="openEdit(bar.id)"
        >
          {{ bar.displayName }}
        </button>
      </button>
    </div>

    <div v-else-if="view === 'year'" class="year-view">
      <div
        v-for="(monthName, monthIndex) in monthLabels"
        :key="monthIndex"
        class="year-row"
        role="button"
        tabindex="0"
        @click="openCreateForMonth(monthIndex)"
      >
        <div class="year-label">{{ monthName }}</div>
        <div class="year-track">
          <button
            v-for="bar in barsInMonth(monthIndex)"
            :key="bar.id"
            type="button"
            class="year-bar"
            :class="{ 'year-bar--empty': !bar.filled }"
            :style="yearBarStyle(bar, monthIndex)"
            :title="bar.displayName"
            @click.stop="openEdit(bar.id)"
          >
            {{ bar.displayName }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="fleet-view">
      <div v-for="group in fleetGroups" :key="group.type" class="fleet-group">
        <h3><ApplianceTypeChip :type="group.type" /></h3>
        <div class="fleet-table">
          <div class="fleet-head" :style="fleetGridStyle">
            <div class="fleet-name-col" />
            <div v-for="day in fleetDays" :key="day" class="fleet-day">{{ day }}</div>
          </div>
          <div v-for="appliance in group.appliances" :key="appliance.id" class="fleet-row" :style="fleetGridStyle">
            <div class="fleet-name-col">{{ appliance.name || `#${appliance.id}` }}</div>
            <button
              v-for="iso in fleetIsos"
              :key="iso"
              type="button"
              class="fleet-cell"
              :class="{ 'fleet-cell--busy': occupancyOnDay(appliance.occupancies, iso) }"
              :style="fleetCellStyle(appliance, iso)"
              :title="occupancyOnDay(appliance.occupancies, iso)?.displayName || ''"
              @click="onFleetCell(appliance, iso)"
            />
          </div>
        </div>
      </div>
    </div>

    <v-dialog v-model="dialogOpen" max-width="32rem">
      <v-card>
        <v-card-title>{{ dialogTitle }}</v-card-title>
        <v-card-text>
          <p v-if="dialogError" class="error mb-3">{{ dialogError }}</p>

          <template v-if="dialogMode === 'edit'">
            <p data-testid="org-readonly" class="org-readonly mb-3">
              <span class="muted">{{ $t('common.organisation') }}:</span>
              {{ editRental?.organisation_name }}
            </p>
          </template>
          <v-select
            v-else
            v-model="form.organisationId"
            :items="organisationItems"
            item-title="title"
            item-value="value"
            :label="$t('common.organisation')"
            hide-details="auto"
            class="mb-3"
          />

          <v-text-field v-model="form.label" :label="$t('rentals.labelOptional')" hide-details="auto" class="mb-3" />
          <v-text-field v-model="form.startDate" type="date" :label="$t('lending.startDate')" hide-details="auto" class="mb-3" />
          <v-text-field v-model="form.endDate" type="date" :label="$t('lending.endDate')" hide-details="auto" />

          <div v-if="dialogMode === 'edit'" class="lendings-block">
            <h4>{{ $t('rentals.devices') }}</h4>
            <p v-if="!(editRental?.lendings?.length)" class="muted">{{ $t('rentals.noDevices') }}</p>
            <ul v-else class="lending-list">
              <li v-for="row in editRental?.lendings || []" :key="row.id" class="lending-row">
                <span>
                  {{ row.appliance_name || `#${row.appliance_id}` }}
                  <span class="muted">({{ segmentLabel(row.segment) }})</span>
                </span>
                <v-btn
                  v-if="row.segment === 'future'"
                  size="small"
                  data-testid="lending-unassign"
                  :loading="lendingBusyId === row.id"
                  @click="unassignLending(row.id)"
                >
                  {{ $t('rentals.unassignDevice') }}
                </v-btn>
                <v-btn
                  v-else-if="row.segment === 'current'"
                  size="small"
                  data-testid="lending-return"
                  :loading="lendingBusyId === row.id"
                  @click="unassignLending(row.id)"
                >
                  {{ $t('rentals.returnDevice') }}
                </v-btn>
              </li>
            </ul>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="dialogMode === 'edit' && canDeleteEdit"
            color="error"
            data-testid="rental-delete"
            :loading="deleting"
            @click="deleteRental"
          >
            {{ $t('rentals.delete') }}
          </v-btn>
          <v-spacer />
          <v-btn variant="outlined" @click="dialogOpen = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" data-testid="rental-save" :loading="saving" @click="saveDialog">{{ $t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import HelpLink from './HelpLink.vue'
import ApplianceTypeChip from './ApplianceTypeChip.vue'
import { apiJson } from '../api'
import { isApiError } from '@/types/api'
import type { FleetRead, OrganisationRead, RentalRead } from '@/types/api'
import {
  clipRangeToMonth,
  isoDate,
  monthGrid,
  occupancyOnDay,
  organisationBarColor,
  parseIsoDate,
  rentalCanDelete,
  rentalsOverlappingMonth,
  type FleetOccupancy,
  type FleetTypeGroup,
  type RentalBar,
} from '../utils/rentalCalendar'
import { currentLocale } from '../i18n'

type CalendarView = 'month' | 'year' | 'fleet'
type DialogMode = 'create' | 'edit' | 'assign'

const { t } = useI18n()
const view = ref<CalendarView>('month')
const cursor = ref(new Date())
const loading = ref(false)
const message = ref('')
const messageType = ref('')
const rentals = ref<RentalBar[]>([])
const fleetGroups = ref<FleetTypeGroup[]>([])
const organisations = ref<OrganisationRead[]>([])
const dialogOpen = ref(false)
const dialogMode = ref<DialogMode>('create')
const dialogError = ref('')
const saving = ref(false)
const deleting = ref(false)
const lendingBusyId = ref<number | null>(null)
const assignAppliance = ref<number | null>(null)
const editRental = ref<RentalRead | null>(null)
const form = reactive({
  organisationId: null as number | null,
  label: '',
  startDate: '',
  endDate: '',
})

const year = computed(() => cursor.value.getFullYear())
const month = computed(() => cursor.value.getMonth())

const periodLabel = computed(() => {
  const loc = currentLocale()
  if (view.value === 'year') return String(year.value)
  return cursor.value.toLocaleDateString(loc === 'en' ? 'en-GB' : 'de-CH', { month: 'long', year: 'numeric' })
})

const weekdayLabels = computed(() => {
  const loc = currentLocale() === 'en' ? 'en-GB' : 'de-CH'
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(2026, 5, 8 + i)
    return d.toLocaleDateString(loc, { weekday: 'short' })
  })
})

const monthLabels = computed(() => {
  const loc = currentLocale() === 'en' ? 'en-GB' : 'de-CH'
  return Array.from({ length: 12 }, (_, i) => new Date(2026, i, 1).toLocaleDateString(loc, { month: 'short' }))
})

const monthCells = computed(() => monthGrid(year.value, month.value))

const fleetDays = computed(() => {
  const last = new Date(year.value, month.value + 1, 0).getDate()
  return Array.from({ length: last }, (_, i) => i + 1)
})

const fleetIsos = computed(() =>
  fleetDays.value.map((day) => isoDate(new Date(year.value, month.value, day))),
)

const fleetGridStyle = computed(() => ({
  gridTemplateColumns: `9rem repeat(${fleetDays.value.length}, minmax(1.4rem, 1fr))`,
}))

const organisationItems = computed(() =>
  organisations.value.map((org) => ({ title: org.name, value: org.id })),
)

const dialogTitle = computed(() => {
  if (dialogMode.value === 'edit') return t('rentals.editTitle')
  if (assignAppliance.value != null) return t('rentals.assignTitle')
  return t('rentals.createTitle')
})

const canDeleteEdit = computed(() => rentalCanDelete(editRental.value?.lendings ?? []))

function toBar(row: RentalRead): RentalBar {
  return {
    id: row.id,
    displayName: row.display_name,
    organisationId: row.organisation_id,
    startDate: row.start_date,
    endDate: row.end_date,
    filled: row.filled,
  }
}

function segmentLabel(segment: string): string {
  if (segment === 'future') return t('rentals.segmentPlanned')
  if (segment === 'current') return t('rentals.segmentCurrent')
  return t('rentals.segmentPast')
}

function rangeForView(): { from: string; to: string } {
  if (view.value === 'year') {
    return { from: `${year.value}-01-01`, to: `${year.value}-12-31` }
  }
  const start = isoDate(new Date(year.value, month.value, 1))
  const end = isoDate(new Date(year.value, month.value + 1, 0))
  return { from: start, to: end }
}

async function load() {
  loading.value = true
  message.value = ''
  try {
    const { from, to } = rangeForView()
    const rows = await apiJson<RentalRead[]>(`/rentals/?from=${from}&to=${to}`)
    rentals.value = rows.map(toBar)
    if (view.value === 'fleet') {
      const fleet = await apiJson<FleetRead>(`/rentals/fleet?year=${year.value}&month=${month.value + 1}`)
      fleetGroups.value = fleet.groups.map((group) => ({
        type: group.type,
        appliances: group.appliances.map((appliance) => ({
          id: appliance.id,
          name: appliance.name,
          type: appliance.type,
          occupancies: appliance.occupancies.map(
            (occ): FleetOccupancy => ({
              rentalId: occ.rental_id,
              displayName: occ.display_name,
              organisationId: occ.organisation_id,
              startDate: occ.start_date,
              endDate: occ.end_date,
            }),
          ),
        })),
      }))
    }
  } catch (err: unknown) {
    message.value = isApiError(err) ? err.message || t('rentals.loadError') : t('rentals.loadError')
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function loadOrganisations() {
  try {
    organisations.value = await apiJson<OrganisationRead[]>('/organisations/')
  } catch {
    organisations.value = []
  }
}

function barsOnDay(iso: string): RentalBar[] {
  return rentals.value.filter((bar) => bar.startDate <= iso && iso <= bar.endDate)
}

function barsInMonth(monthIndex: number): RentalBar[] {
  return rentalsOverlappingMonth(rentals.value, year.value, monthIndex)
}

function yearBarStyle(bar: RentalBar, monthIndex: number) {
  const clipped = clipRangeToMonth(bar.startDate, bar.endDate, year.value, monthIndex)
  if (!clipped) return { display: 'none' }
  const days = new Date(year.value, monthIndex + 1, 0).getDate()
  const startDay = parseIsoDate(clipped.start).getDate()
  const endDay = parseIsoDate(clipped.end).getDate()
  const left = ((startDay - 1) / days) * 100
  const width = ((endDay - startDay + 1) / days) * 100
  return {
    left: `${left}%`,
    width: `${Math.max(width, 4)}%`,
    background: organisationBarColor(bar.organisationId),
  }
}

function fleetCellStyle(appliance: { occupancies: FleetOccupancy[] }, iso: string) {
  const occ = occupancyOnDay(appliance.occupancies, iso)
  if (!occ) return undefined
  return { background: organisationBarColor(occ.organisationId) }
}

function shift(delta: number) {
  const next = new Date(cursor.value)
  if (view.value === 'year') next.setFullYear(next.getFullYear() + delta)
  else next.setMonth(next.getMonth() + delta)
  cursor.value = next
}

function goToday() {
  cursor.value = new Date()
}

function openCreate(iso?: string, endIso?: string) {
  dialogMode.value = 'create'
  dialogError.value = ''
  editRental.value = null
  assignAppliance.value = null
  form.organisationId = organisations.value[0]?.id ?? null
  form.label = ''
  form.startDate = iso ?? isoDate(new Date())
  form.endDate = endIso ?? form.startDate
  dialogOpen.value = true
}

function openCreateForMonth(monthIndex: number) {
  const start = isoDate(new Date(year.value, monthIndex, 1))
  const end = isoDate(new Date(year.value, monthIndex + 1, 0))
  openCreate(start, end)
}

async function openEdit(rentalId: number) {
  dialogMode.value = 'edit'
  dialogError.value = ''
  assignAppliance.value = null
  dialogOpen.value = true
  try {
    const row = await apiJson<RentalRead>(`/rentals/${rentalId}`)
    editRental.value = row
    form.organisationId = row.organisation_id
    form.label = row.label ?? ''
    form.startDate = row.start_date
    form.endDate = row.end_date
  } catch (err: unknown) {
    dialogOpen.value = false
    message.value = isApiError(err) ? err.message || t('rentals.loadError') : t('rentals.loadError')
    messageType.value = 'error'
  }
}

function onFleetCell(appliance: { id: number; occupancies: FleetOccupancy[] }, iso: string) {
  if (occupancyOnDay(appliance.occupancies, iso)) return
  dialogMode.value = 'assign'
  dialogError.value = ''
  editRental.value = null
  assignAppliance.value = appliance.id
  form.organisationId = organisations.value[0]?.id ?? null
  form.label = ''
  form.startDate = iso
  form.endDate = iso
  dialogOpen.value = true
}

async function saveDialog() {
  dialogError.value = ''
  if (form.endDate < form.startDate) {
    dialogError.value = t('lending.endDateRangeError')
    return
  }
  if (dialogMode.value === 'edit') {
    if (editRental.value == null) return
    saving.value = true
    try {
      const updated = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: form.label.trim() || null,
          start_date: form.startDate,
          end_date: form.endDate,
        }),
      })
      editRental.value = updated
      message.value = t('rentals.updateSuccess')
      messageType.value = 'success'
      dialogOpen.value = false
      await load()
    } catch (err: unknown) {
      dialogError.value = isApiError(err) ? err.message || t('rentals.saveFailed') : t('rentals.saveFailed')
      try {
        editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`)
        form.label = editRental.value.label ?? ''
        form.startDate = editRental.value.start_date
        form.endDate = editRental.value.end_date
      } catch {
        // keep form values
      }
    } finally {
      saving.value = false
    }
    return
  }

  if (form.organisationId == null) {
    dialogError.value = t('rentals.noOrganisation')
    return
  }
  saving.value = true
  try {
    const existing = rentals.value.find(
      (row) =>
        row.organisationId === form.organisationId &&
        row.startDate === form.startDate &&
        row.endDate === form.endDate,
    )
    if (assignAppliance.value != null && existing) {
      await apiJson(`/rentals/${existing.id}/appliances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appliance_id: assignAppliance.value }),
      })
      message.value = t('rentals.assignSuccess')
    } else {
      await apiJson('/rentals/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organisation_id: form.organisationId,
          start_date: form.startDate,
          end_date: form.endDate,
          label: form.label.trim() || null,
          appliance_ids: assignAppliance.value != null ? [assignAppliance.value] : [],
        }),
      })
      message.value = assignAppliance.value != null ? t('rentals.assignSuccess') : t('rentals.createSuccess')
    }
    messageType.value = 'success'
    dialogOpen.value = false
    await load()
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.saveFailed') : t('rentals.saveFailed')
  } finally {
    saving.value = false
  }
}

async function unassignLending(lendingId: number) {
  if (editRental.value == null) return
  lendingBusyId.value = lendingId
  dialogError.value = ''
  try {
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}/lendings/${lendingId}`, {
      method: 'DELETE',
    })
    message.value = t('rentals.deviceActionSuccess')
    messageType.value = 'success'
    await load()
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.saveFailed') : t('rentals.saveFailed')
  } finally {
    lendingBusyId.value = null
  }
}

async function deleteRental() {
  if (editRental.value == null || !canDeleteEdit.value) return
  if (!confirm(t('rentals.deleteConfirm', { name: editRental.value.display_name }))) return
  deleting.value = true
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${editRental.value.id}`, { method: 'DELETE' })
    message.value = t('rentals.deleteSuccess')
    messageType.value = 'success'
    dialogOpen.value = false
    editRental.value = null
    await load()
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.deleteFailed') : t('rentals.deleteFailed')
  } finally {
    deleting.value = false
  }
}

watch([view, cursor], () => {
  void load()
})

onMounted(() => {
  void loadOrganisations()
  void load()
})

defineExpose({
  setViewForTest(next: CalendarView) {
    view.value = next
  },
})
</script>

<style scoped>
.rentals-calendar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0 2rem;
}
.rentals-header,
.toolbar,
.nav-period,
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.rentals-header {
  justify-content: space-between;
}
.toolbar {
  flex-wrap: wrap;
}
.muted {
  opacity: 0.7;
  margin: 0.25rem 0 0;
}
.month-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 2px;
}
.weekday {
  font-size: 0.75rem;
  font-weight: 700;
  opacity: 0.65;
  text-align: center;
  padding: 0.25rem;
}
.day-cell {
  min-height: 6rem;
  border: 1px solid rgba(var(--v-border-color), 0.2);
  background: transparent;
  text-align: left;
  padding: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  cursor: pointer;
}
.day-cell--outside {
  opacity: 0.4;
}
.day-num {
  font-size: 0.8rem;
  font-weight: 600;
}
.rental-chip,
.year-bar {
  color: #fff;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  padding: 0.1rem 0.3rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: none;
  cursor: pointer;
  text-align: left;
}
.rental-chip--empty,
.year-bar--empty {
  background: transparent !important;
  color: inherit;
  border: 1px dashed currentColor;
}
.year-view {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.year-row {
  display: grid;
  grid-template-columns: 4rem 1fr;
  gap: 0.5rem;
  align-items: center;
  cursor: pointer;
}
.year-track {
  position: relative;
  height: 1.5rem;
  background: rgba(var(--v-border-color), 0.08);
  border-radius: 0.25rem;
}
.year-bar {
  position: absolute;
  top: 0.15rem;
  height: 1.2rem;
}
.fleet-group h3 {
  margin: 1rem 0 0.35rem;
}
.fleet-table {
  overflow-x: auto;
}
.fleet-head,
.fleet-row {
  display: grid;
  align-items: stretch;
}
.fleet-name-col {
  font-size: 0.8rem;
  padding: 0.2rem 0.4rem;
}
.fleet-day {
  font-size: 0.65rem;
  text-align: center;
  opacity: 0.7;
}
.fleet-cell {
  min-height: 1.4rem;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  background: transparent;
  padding: 0;
  cursor: pointer;
}
.fleet-cell--busy {
  cursor: default;
}
.org-readonly {
  margin: 0;
  font-weight: 600;
}
.lendings-block {
  margin-top: 1rem;
}
.lendings-block h4 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
}
.lending-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.lending-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.error {
  color: rgb(var(--v-theme-error));
}
.success {
  color: rgb(var(--v-theme-success));
}
.mb-3 {
  margin-bottom: 0.75rem;
}
</style>
