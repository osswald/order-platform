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

    <p v-if="message" :class="messageType" data-testid="rentals-message">{{ message }}</p>
    <p v-if="loading" class="muted" data-testid="rentals-loading">{{ $t('common.loading') }}</p>

    <div v-show="view === 'month'" class="month-grid" data-testid="month-grid">
      <div v-for="wd in weekdayLabels" :key="wd" class="weekday">{{ wd }}</div>
      <div v-for="(week, weekIndex) in monthWeekRows" :key="weekIndex" class="month-week">
        <div class="month-week-days">
          <button
            v-for="cell in week"
            :key="cell.iso"
            type="button"
            class="day-cell"
            :class="{ 'day-cell--outside': !cell.inMonth }"
            @click="openCreate(cell.iso)"
          >
            <span class="day-num">{{ cell.date.getDate() }}</span>
          </button>
        </div>
        <div
          class="month-week-bars"
          :style="{ minHeight: `${Math.max(monthLaneCount(weekIndex), 1) * 1.35}rem` }"
        >
          <v-tooltip
            v-for="{ seg, rental } in segmentsWithRental(weekIndex)"
            :key="`${seg.rentalId}-${seg.weekIndex}-${seg.startCol}`"
            location="top"
            open-delay="250"
          >
            <template #activator="{ props: tipProps }">
              <button
                v-bind="tipProps"
                type="button"
                class="month-bar"
                :class="{ 'month-bar--empty': !seg.filled }"
                :style="monthBarStyle(seg)"
                data-testid="month-rental-bar"
                @click.stop="openEdit(seg.rentalId)"
              >
                {{ seg.displayName }}
              </button>
            </template>
            <div class="rental-tooltip" data-testid="rental-bar-tooltip">
              <div class="rental-tooltip-title">{{ rental.displayName }}</div>
              <div v-if="rental.organisationName !== rental.displayName">
                {{ rental.organisationName }}
              </div>
              <div>{{ formatRentalRange(rental.startDate, rental.endDate) }}</div>
              <div class="rental-tooltip-devices">{{ $t('rentals.devices') }}</div>
              <ul v-if="rental.applianceNames.length" class="rental-tooltip-list">
                <li v-for="name in rental.applianceNames" :key="name">{{ name }}</li>
              </ul>
              <div v-else class="muted">{{ $t('rentals.noDevices') }}</div>
            </div>
          </v-tooltip>
        </div>
      </div>
    </div>

    <div v-show="view === 'year'" class="year-view" data-testid="year-view">
      <div
        v-for="(monthName, monthIndex) in monthLabels"
        :key="monthIndex"
        class="year-row"
        role="button"
        tabindex="0"
        @click="openCreateForMonth(monthIndex)"
      >
        <div class="year-label">{{ monthName }}</div>
        <div
          class="year-track"
          :style="{ height: `${Math.max(yearLaneCount(monthIndex), 1) * 1.45}rem` }"
        >
          <v-tooltip
            v-for="bar in yearBarsForMonth(monthIndex)"
            :key="bar.id"
            location="top"
            open-delay="250"
          >
            <template #activator="{ props: tipProps }">
              <button
                v-bind="tipProps"
                type="button"
                class="year-bar"
                :class="{ 'year-bar--empty': !bar.filled }"
                :style="yearBarStyle(bar, monthIndex)"
                data-testid="year-rental-bar"
                @click.stop="openEdit(bar.id)"
              >
                {{ bar.displayName }}
              </button>
            </template>
            <div class="rental-tooltip" data-testid="rental-bar-tooltip">
              <div class="rental-tooltip-title">{{ bar.displayName }}</div>
              <div v-if="bar.organisationName !== bar.displayName">{{ bar.organisationName }}</div>
              <div>{{ formatRentalRange(bar.startDate, bar.endDate) }}</div>
              <div class="rental-tooltip-devices">{{ $t('rentals.devices') }}</div>
              <ul v-if="bar.applianceNames.length" class="rental-tooltip-list">
                <li v-for="name in bar.applianceNames" :key="name">{{ name }}</li>
              </ul>
              <div v-else class="muted">{{ $t('rentals.noDevices') }}</div>
            </div>
          </v-tooltip>
        </div>
      </div>
    </div>

    <div v-show="view === 'fleet'" class="fleet-view">
      <div v-for="group in fleetGroups" :key="group.type" class="fleet-group">
        <h3><ApplianceTypeChip :type="group.type" /></h3>
        <div class="fleet-table">
          <div class="fleet-head" :style="fleetGridStyle">
            <div class="fleet-name-col" />
            <div v-for="day in fleetDays" :key="day" class="fleet-day">{{ day }}</div>
          </div>
          <div v-for="appliance in group.appliances" :key="appliance.id" class="fleet-row" :style="fleetGridStyle">
            <div class="fleet-name-col">{{ fleetApplianceLabel(appliance) }}</div>
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
            data-testid="org-select"
          />

          <v-text-field v-model="form.label" :label="$t('rentals.labelOptional')" hide-details="auto" class="mb-3" />
          <v-text-field v-model="form.startDate" type="date" :label="$t('lending.startDate')" hide-details="auto" class="mb-3" />
          <v-text-field v-model="form.endDate" type="date" :label="$t('lending.endDate')" hide-details="auto" />

          <div v-if="dialogMode === 'edit'" class="lendings-block">
            <h4>{{ $t('rentals.devices') }}</h4>
            <p v-if="!(editRental?.lendings?.length)" class="muted">{{ $t('rentals.noDevices') }}</p>
            <ul v-else class="lending-list">
              <li v-for="row in editRental?.lendings || []" :key="row.id" class="lending-row">
                <span class="lending-label">
                  <ApplianceTypeChip :type="row.appliance_type" data-testid="lending-appliance-type" />
                  <span>
                    {{ lendingApplianceLabel(row) }}
                    <span class="muted">({{ segmentLabel(row.segment) }})</span>
                  </span>
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
            <div class="zubehoer-add-row">
              <v-select
                v-model="pickApplianceId"
                :items="addApplianceItems"
                item-title="title"
                item-value="value"
                :label="$t('rentals.addDevice')"
                hide-details="auto"
                clearable
                :loading="loadingAddAppliances"
                data-testid="rental-add-appliance-pick"
                class="zubehoer-pick"
              >
                <template #item="{ item, props: itemProps }">
                  <v-list-item v-bind="itemProps" :title="undefined">
                    <div class="appliance-pick-row">
                      <ApplianceTypeChip
                        :type="appliancePickType(item)"
                        data-testid="add-appliance-type"
                      />
                      <span>{{ appliancePickTitle(item) }}</span>
                    </div>
                  </v-list-item>
                </template>
                <template #selection="{ item }">
                  <div class="appliance-pick-row">
                    <ApplianceTypeChip :type="appliancePickType(item)" />
                    <span>{{ appliancePickTitle(item) }}</span>
                  </div>
                </template>
              </v-select>
              <v-btn
                size="small"
                data-testid="rental-add-appliance"
                :disabled="pickApplianceId == null"
                :loading="addingAppliance"
                @click="addApplianceToRental"
              >
                {{ $t('rentals.addDeviceAction') }}
              </v-btn>
            </div>
          </div>

          <div v-if="dialogMode === 'edit'" class="zubehoer-block">
            <h4>{{ $t('rentals.zubehoer') }}</h4>
            <p v-if="!(editRental?.zubehoer_lines?.length)" class="muted">{{ $t('rentals.noZubehoer') }}</p>
            <ul v-else class="zubehoer-list">
              <li v-for="line in editRental?.zubehoer_lines || []" :key="line.id" class="zubehoer-row">
                <template v-if="editingZubehoerId === line.id">
                  <div class="zubehoer-edit-fields">
                    <v-text-field
                      v-model="editZubehoerLabel"
                      :label="$t('rentals.freeTextLabel')"
                      hide-details="auto"
                      class="zubehoer-pick"
                      data-testid="zubehoer-edit-label"
                    />
                    <v-text-field
                      v-model="editZubehoerQty"
                      type="number"
                      min="1"
                      :label="$t('rentals.qtyOptional')"
                      hide-details="auto"
                      class="zubehoer-qty"
                      data-testid="zubehoer-edit-qty"
                    />
                  </div>
                  <span class="row-actions">
                    <v-btn
                      size="small"
                      color="primary"
                      data-testid="zubehoer-line-save"
                      :loading="zubehoerBusyId === line.id"
                      :disabled="!editZubehoerLabel.trim()"
                      @click="saveZubehoerLine(line.id)"
                    >
                      {{ $t('common.save') }}
                    </v-btn>
                    <v-btn size="small" data-testid="zubehoer-line-cancel" @click="cancelZubehoerEdit">
                      {{ $t('common.cancel') }}
                    </v-btn>
                  </span>
                </template>
                <template v-else>
                  <span>
                    {{ line.label }}
                    <span v-if="line.quantity != null" class="muted">({{ line.quantity }})</span>
                  </span>
                  <span class="row-actions">
                    <v-btn
                      size="small"
                      data-testid="zubehoer-line-edit"
                      @click="startZubehoerEdit(line)"
                    >
                      {{ $t('common.edit') }}
                    </v-btn>
                    <v-btn
                      size="small"
                      color="error"
                      data-testid="zubehoer-line-delete"
                      :loading="zubehoerBusyId === line.id"
                      @click="removeZubehoerLine(line.id)"
                    >
                      {{ $t('common.delete') }}
                    </v-btn>
                  </span>
                </template>
              </li>
            </ul>
            <div class="zubehoer-add-row">
              <v-select
                v-model="pickCatalogId"
                :items="catalogPickItems"
                item-title="title"
                item-value="value"
                :label="$t('rentals.addFromCatalog')"
                hide-details="auto"
                clearable
                data-testid="zubehoer-catalog-pick"
                class="zubehoer-pick"
              />
              <v-btn
                size="small"
                data-testid="zubehoer-add-catalog"
                :disabled="pickCatalogId == null"
                :loading="zubehoerAdding"
                @click="addFromCatalog"
              >
                {{ $t('rentals.addZubehoer') }}
              </v-btn>
            </div>
            <div class="zubehoer-add-row">
              <v-text-field
                v-model="freeTextLabel"
                :label="$t('rentals.freeTextLabel')"
                hide-details="auto"
                class="zubehoer-pick"
                data-testid="zubehoer-free-text"
              />
              <v-text-field
                v-model="freeTextQty"
                type="number"
                min="1"
                :label="$t('rentals.qtyOptional')"
                hide-details="auto"
                class="zubehoer-qty"
              />
              <v-btn
                size="small"
                data-testid="zubehoer-add-free-text"
                :disabled="!freeTextLabel.trim()"
                :loading="zubehoerAdding"
                @click="addFreeTextLine"
              >
                {{ $t('rentals.addZubehoer') }}
              </v-btn>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="dialogMode === 'edit'"
            variant="outlined"
            data-testid="rental-packing-pdf"
            :loading="packingPdfLoading"
            @click="downloadPackingPdf"
          >
            {{ $t('rentals.packingListPdf') }}
          </v-btn>
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
import { apiFetch, apiJson } from '../api'
import { isApiError } from '@/types/api'
import type {
  ApplianceRead,
  FleetRead,
  OrganisationRead,
  RentalRead,
  RentalZubehoerCatalogRead,
  RentalZubehoerLineRead,
} from '@/types/api'
import {
  isoDate,
  monthBarSegments,
  monthWeeks,
  occupancyOnDay,
  openRentalApplianceNames,
  organisationBarColor,
  parseIsoDate,
  rentalApplianceLabel,
  rentalCanDelete,
  yearBarsWithLanes,
  type FleetOccupancy,
  type FleetTypeGroup,
  type MonthBarSegment,
  type RentalBar,
} from '../utils/rentalCalendar'
import { formatDate } from '../utils/localeFormat'
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
const addingAppliance = ref(false)
const loadingAddAppliances = ref(false)
const pickApplianceId = ref<number | null>(null)
const addApplianceCandidates = ref<ApplianceRead[]>([])
const zubehoerBusyId = ref<number | null>(null)
const zubehoerAdding = ref(false)
const packingPdfLoading = ref(false)
const catalogItems = ref<RentalZubehoerCatalogRead[]>([])
const pickCatalogId = ref<number | null>(null)
const freeTextLabel = ref('')
const freeTextQty = ref('')
const editingZubehoerId = ref<number | null>(null)
const editZubehoerLabel = ref('')
const editZubehoerQty = ref('')
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

const monthWeekRows = computed(() => monthWeeks(year.value, month.value))
const monthSegments = computed(() => monthBarSegments(rentals.value, year.value, month.value))

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

const catalogPickItems = computed(() =>
  catalogItems.value
    .filter((item) => item.is_active)
    .map((item) => ({
      title: item.default_quantity != null ? `${item.name} (${item.default_quantity})` : item.name,
      value: item.id,
    })),
)

const assignedOpenApplianceIds = computed(() => {
  const ids = new Set<number>()
  for (const row of editRental.value?.lendings ?? []) {
    if (!row.returned_at) ids.add(row.appliance_id)
  }
  return ids
})

const addApplianceItems = computed(() =>
  addApplianceCandidates.value
    .filter((row) => row.lendable !== false && !assignedOpenApplianceIds.value.has(row.id))
    .map((row) => ({
      title: rentalApplianceLabel({
        id: row.id,
        name: row.name,
        type: row.type,
        ip_address: row.ip_address,
      }),
      value: row.id,
      type: row.type,
    })),
)

async function loadCatalog() {
  try {
    catalogItems.value = await apiJson<RentalZubehoerCatalogRead[]>('/rental-zubehoer-catalog/')
  } catch {
    catalogItems.value = []
  }
}

async function loadAddApplianceCandidates() {
  if (editRental.value == null) {
    addApplianceCandidates.value = []
    return
  }
  loadingAddAppliances.value = true
  try {
    const start = editRental.value.start_date
    const end = editRental.value.end_date
    const duration =
      Math.round((parseIsoDate(end).getTime() - parseIsoDate(start).getTime()) / 86400000) + 1
    const params = new URLSearchParams({
      lend_check_start: start,
      lend_check_duration: String(Math.max(duration, 1)),
    })
    addApplianceCandidates.value = await apiJson<ApplianceRead[]>(`/appliances/?${params}`)
  } catch {
    addApplianceCandidates.value = []
  } finally {
    loadingAddAppliances.value = false
  }
}

async function addApplianceToRental() {
  if (editRental.value == null || pickApplianceId.value == null) return
  addingAppliance.value = true
  dialogError.value = ''
  try {
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}/appliances`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ appliance_id: pickApplianceId.value }),
    })
    pickApplianceId.value = null
    message.value = t('rentals.assignSuccess')
    messageType.value = 'success'
    await loadAddApplianceCandidates()
    await load()
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.addDeviceFailed') : t('rentals.addDeviceFailed')
  } finally {
    addingAppliance.value = false
  }
}

function resetZubehoerDraft() {
  pickCatalogId.value = null
  freeTextLabel.value = ''
  freeTextQty.value = ''
  pickApplianceId.value = null
  cancelZubehoerEdit()
}

function startZubehoerEdit(line: RentalZubehoerLineRead) {
  editingZubehoerId.value = line.id
  editZubehoerLabel.value = line.label
  editZubehoerQty.value = line.quantity != null ? String(line.quantity) : ''
}

function cancelZubehoerEdit() {
  editingZubehoerId.value = null
  editZubehoerLabel.value = ''
  editZubehoerQty.value = ''
}

async function saveZubehoerLine(lineId: number) {
  if (editRental.value == null) return
  const label = editZubehoerLabel.value.trim()
  if (!label) return
  const qtyTrimmed = editZubehoerQty.value.trim()
  const payload: { label: string; quantity: number | null } = { label, quantity: null }
  if (qtyTrimmed) {
    const qty = Number.parseInt(qtyTrimmed, 10)
    if (Number.isFinite(qty) && qty >= 1) payload.quantity = qty
  }
  zubehoerBusyId.value = lineId
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${editRental.value.id}/zubehoer-lines/${lineId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`)
    cancelZubehoerEdit()
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.zubehoerSaveFailed') : t('rentals.zubehoerSaveFailed')
  } finally {
    zubehoerBusyId.value = null
  }
}

async function addFromCatalog() {
  if (editRental.value == null || pickCatalogId.value == null) return
  zubehoerAdding.value = true
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${editRental.value.id}/zubehoer-lines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ catalog_item_id: pickCatalogId.value }),
    })
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`)
    pickCatalogId.value = null
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.zubehoerSaveFailed') : t('rentals.zubehoerSaveFailed')
  } finally {
    zubehoerAdding.value = false
  }
}

async function addFreeTextLine() {
  if (editRental.value == null) return
  const label = freeTextLabel.value.trim()
  if (!label) return
  const qtyTrimmed = freeTextQty.value.trim()
  const payload: { label: string; quantity?: number } = { label }
  if (qtyTrimmed) {
    const qty = Number.parseInt(qtyTrimmed, 10)
    if (Number.isFinite(qty) && qty >= 1) payload.quantity = qty
  }
  zubehoerAdding.value = true
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${editRental.value.id}/zubehoer-lines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`)
    freeTextLabel.value = ''
    freeTextQty.value = ''
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.zubehoerSaveFailed') : t('rentals.zubehoerSaveFailed')
  } finally {
    zubehoerAdding.value = false
  }
}

async function removeZubehoerLine(lineId: number) {
  if (editRental.value == null) return
  zubehoerBusyId.value = lineId
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${editRental.value.id}/zubehoer-lines/${lineId}`, { method: 'DELETE' })
    editRental.value = await apiJson<RentalRead>(`/rentals/${editRental.value.id}`)
  } catch (err: unknown) {
    dialogError.value = isApiError(err) ? err.message || t('rentals.zubehoerSaveFailed') : t('rentals.zubehoerSaveFailed')
  } finally {
    zubehoerBusyId.value = null
  }
}

async function downloadPackingPdf() {
  if (editRental.value == null) return
  packingPdfLoading.value = true
  dialogError.value = ''
  try {
    const response = await apiFetch(`/rentals/${editRental.value.id}/packing-list.pdf`, {
      headers: { 'Accept-Language': currentLocale() === 'en' ? 'en' : 'de' },
    })
    if (!response.ok) throw new Error(t('rentals.packingListPdfFailed'))
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    const safeName = (editRental.value.display_name || 'Packliste').replace(/[^\w\s-]+/g, '').trim().replace(/\s+/g, '-') || 'Packliste'
    anchor.href = url
    anchor.download = `Packliste-${safeName}.pdf`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (err: unknown) {
    dialogError.value = err instanceof Error ? err.message : t('rentals.packingListPdfFailed')
  } finally {
    packingPdfLoading.value = false
  }
}

function toBar(row: RentalRead): RentalBar {
  return {
    id: row.id,
    displayName: row.display_name,
    organisationId: row.organisation_id,
    organisationName: row.organisation_name,
    startDate: row.start_date,
    endDate: row.end_date,
    filled: row.filled,
    applianceNames: openRentalApplianceNames(row.lendings),
  }
}

function formatRentalRange(startDate?: string, endDate?: string): string {
  if (!startDate || !endDate) return '—'
  return `${formatDate(startDate, currentLocale())} – ${formatDate(endDate, currentLocale())}`
}

function rentalById(id: number): RentalBar | undefined {
  return rentals.value.find((row) => row.id === id)
}

function segmentsWithRental(weekIndex: number): Array<{ seg: MonthBarSegment; rental: RentalBar }> {
  const out: Array<{ seg: MonthBarSegment; rental: RentalBar }> = []
  for (const seg of segmentsInWeek(weekIndex)) {
    const rental = rentalById(seg.rentalId)
    if (rental) out.push({ seg, rental })
  }
  return out
}

function appliancePickType(item: { type?: string; raw?: { type?: string } }): string {
  return item.raw?.type || item.type || ''
}

function appliancePickTitle(item: { title?: string; raw?: { title?: string } }): string {
  return item.raw?.title || item.title || ''
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

async function load(options: { preserveMessage?: boolean } = {}) {
  loading.value = true
  if (!options.preserveMessage) {
    message.value = ''
  }
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
          ipAddress: appliance.ip_address ?? null,
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

function lendingApplianceLabel(row: {
  appliance_id: number
  appliance_name?: string | null
  appliance_type: string
  appliance_ip_address?: string | null
}): string {
  return rentalApplianceLabel({
    id: row.appliance_id,
    name: row.appliance_name,
    type: row.appliance_type,
    ip_address: row.appliance_ip_address,
  })
}

function fleetApplianceLabel(appliance: {
  id: number
  name: string | null
  type: string
  ipAddress: string | null
}): string {
  return rentalApplianceLabel({
    id: appliance.id,
    name: appliance.name,
    type: appliance.type,
    ip_address: appliance.ipAddress,
  })
}

function segmentsInWeek(weekIndex: number): MonthBarSegment[] {
  return monthSegments.value.filter((seg) => seg.weekIndex === weekIndex)
}

function monthLaneCount(weekIndex: number): number {
  const lanes = segmentsInWeek(weekIndex).map((seg) => seg.lane)
  return lanes.length ? Math.max(...lanes) + 1 : 0
}

function monthBarStyle(seg: MonthBarSegment) {
  const left = (seg.startCol / 7) * 100
  const width = ((seg.endCol - seg.startCol + 1) / 7) * 100
  return {
    left: `${left}%`,
    width: `${Math.max(width, 100 / 7)}%`,
    top: `${seg.lane * 1.3}rem`,
    background: organisationBarColor(seg.organisationId),
  }
}

function yearBarsForMonth(monthIndex: number) {
  return yearBarsWithLanes(rentals.value, year.value, monthIndex)
}

function yearLaneCount(monthIndex: number): number {
  const bars = yearBarsForMonth(monthIndex)
  return bars.length ? Math.max(...bars.map((bar) => bar.lane)) + 1 : 0
}

function yearBarStyle(
  bar: RentalBar & { lane: number; clipStart: string; clipEnd: string },
  monthIndex: number,
) {
  const days = new Date(year.value, monthIndex + 1, 0).getDate()
  const startDay = parseIsoDate(bar.clipStart).getDate()
  const endDay = parseIsoDate(bar.clipEnd).getDate()
  const left = ((startDay - 1) / days) * 100
  const width = ((endDay - startDay + 1) / days) * 100
  return {
    left: `${left}%`,
    width: `${Math.max(width, 4)}%`,
    top: `${0.15 + bar.lane * 1.35}rem`,
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
  resetZubehoerDraft()
  dialogOpen.value = true
  void loadCatalog()
  try {
    const row = await apiJson<RentalRead>(`/rentals/${rentalId}`)
    editRental.value = row
    form.organisationId = row.organisation_id
    form.label = row.label ?? ''
    form.startDate = row.start_date
    form.endDate = row.end_date
    void loadAddApplianceCandidates()
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
  const deletedId = editRental.value.id
  deleting.value = true
  dialogError.value = ''
  try {
    await apiJson(`/rentals/${deletedId}`, { method: 'DELETE' })
    dialogOpen.value = false
    editRental.value = null
    message.value = t('rentals.deleteSuccess')
    messageType.value = 'success'
    await load({ preserveMessage: true })
    rentals.value = rentals.value.filter((row) => row.id !== deletedId)
  } catch (err: unknown) {
    const errMsg = isApiError(err) ? err.message || t('rentals.deleteFailed') : t('rentals.deleteFailed')
    dialogError.value = errMsg
    message.value = errMsg
    messageType.value = 'error'
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
  setPickApplianceIdForTest(id: number | null) {
    pickApplianceId.value = id
  },
  addApplianceToRentalForTest: addApplianceToRental,
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
.month-week {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  border: 1px solid rgba(var(--v-border-color), 0.2);
  padding: 0.2rem 0 0.35rem;
}
.month-week-days {
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
  min-height: 1.6rem;
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.1rem 0.25rem;
  cursor: pointer;
}
.day-cell--outside {
  opacity: 0.4;
}
.day-num {
  font-size: 0.8rem;
  font-weight: 600;
}
.month-week-bars {
  position: relative;
  width: 100%;
}
.month-bar,
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
.month-bar {
  position: absolute;
  height: 1.15rem;
  box-sizing: border-box;
}
.rental-tooltip {
  max-width: 16rem;
  font-size: 0.8rem;
  line-height: 1.35;
}
.rental-tooltip-title {
  font-weight: 700;
  margin-bottom: 0.15rem;
}
.rental-tooltip-devices {
  margin-top: 0.35rem;
  font-weight: 600;
}
.rental-tooltip-list {
  margin: 0.15rem 0 0;
  padding-left: 1.1rem;
}
.month-bar--empty,
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
  align-items: start;
  cursor: pointer;
}
.year-track {
  position: relative;
  min-height: 1.5rem;
  background: rgba(var(--v-border-color), 0.08);
  border-radius: 0.25rem;
}
.year-bar {
  position: absolute;
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
.lending-label,
.appliance-pick-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.zubehoer-block {
  margin-top: 1rem;
}
.zubehoer-block h4 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
}
.zubehoer-list {
  list-style: none;
  margin: 0 0 0.75rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.zubehoer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.zubehoer-edit-fields {
  display: flex;
  flex: 1;
  gap: 0.5rem;
  min-width: 0;
  flex-wrap: wrap;
}
.row-actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}
.zubehoer-add-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.zubehoer-pick {
  flex: 1 1 10rem;
  min-width: 8rem;
}
.zubehoer-qty {
  flex: 0 1 5rem;
  max-width: 6rem;
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
