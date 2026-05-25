<template>
  <div class="event-config" :class="{ 'event-config--unified': !!$slots.stammdaten }">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <p v-if="configMessage" :class="configMessageType">{{ configMessage }}</p>

      <TabView>
        <TabPanel v-if="$slots.stammdaten" header="Stammdaten">
          <slot name="stammdaten" />
        </TabPanel>
        <TabPanel header="Stationen">
          <div class="section-toolbar">
            <Button label="Station hinzufügen" type="button" class="primary-button" @click="addStation" />
          </div>
          <div v-for="(st, idx) in stationsLocal" :key="'st-' + idx" class="config-card">
            <div class="config-card-header">
              <span>{{ st.name || 'Unbenannte Station' }}</span>
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                type="button"
                aria-label="Entfernen"
                @click="removeStation(idx)"
              />
            </div>
            <div class="form-field">
              <label>Name</label>
              <InputText v-model="st.name" placeholder="z. B. Bar" />
            </div>
            <div class="form-field">
              <label>Drucker</label>
              <Select
                v-model="st.printer_appliance_id"
                :options="printerOptions"
                optionLabel="name"
                optionValue="id"
                placeholder="Kein Drucker"
                showClear
              />
            </div>
            <div class="check-row">
              <Checkbox
                :inputId="'kitchen-monitor-' + idx"
                v-model="st.kitchen_monitor_enabled"
                :binary="true"
              />
              <label :for="'kitchen-monitor-' + idx">Kitchen Monitor aktiv</label>
            </div>
            <div class="form-field">
              <label>Artikel</label>
              <MultiSelect
                v-model="st.article_ids"
                :options="articleOptions"
                optionLabel="name"
                optionValue="value"
                placeholder="Artikel wählen"
                display="chip"
                filter
                class="w-full"
              />
            </div>
          </div>
          <p v-if="!stationsLocal.length" class="muted">Noch keine Stationen.</p>
        </TabPanel>

        <TabPanel header="Event-Kellner">
          <div class="section-toolbar">
            <Button label="Kellner hinzufügen" type="button" class="primary-button" @click="addWaiterRow" />
            <Button label="Aus Organisation übernehmen" type="button" class="secondary-button" @click="openWaiterPick" />
          </div>
          <DataTable :value="waitersLocal" dataKey="_key" class="list-table nested" responsiveLayout="scroll">
            <Column field="name" header="Name">
              <template #body="{ data }">
                <InputText v-model="data.name" class="w-full" />
              </template>
            </Column>
            <Column field="pin" header="PIN">
              <template #body="{ data }">
                <InputText v-model="data.pin" class="w-full" />
              </template>
            </Column>
            <Column header="">
              <template #body="slotProps">
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  type="button"
                  severity="danger"
                  @click="removeWaiter(slotProps.data)"
                />
              </template>
            </Column>
          </DataTable>
        </TabPanel>

        <TabPanel header="Kassen">
          <div class="section-toolbar">
            <Button label="Kasse hinzufügen" type="button" class="primary-button" @click="addCashRegister" />
          </div>
          <div v-for="(reg, ri) in cashRegistersLocal" :key="'reg-' + ri" class="config-card">
            <div class="config-card-header">
              <span>{{ reg.name || 'Unbenannte Kasse' }}</span>
              <Button icon="pi pi-trash" text rounded type="button" severity="danger" @click="removeCashRegister(ri)" />
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Name</label>
                <InputText v-model="reg.name" placeholder="z. B. Hauptkasse" />
              </div>
              <div class="form-field">
                <label>Pickup-Code Buchstaben</label>
                <InputText
                  :modelValue="reg.pickup_code_prefix"
                  maxlength="3"
                  placeholder="A"
                  @update:modelValue="(v) => { reg.pickup_code_prefix = normalizePickupPrefix(v) }"
                />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>PIN</label>
                <InputText v-model="reg.pin" maxlength="4" placeholder="0000" />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Layout</label>
                <Select
                  v-model="reg.layout_uuid"
                  :options="layoutOptions"
                  optionLabel="name"
                  optionValue="value"
                  placeholder="Layout wählen"
                />
              </div>
              <div class="form-field">
                <label>Kundendrucker</label>
                <Select
                  v-model="reg.receipt_printer_appliance_id"
                  :options="printerOptions"
                  optionLabel="name"
                  optionValue="id"
                  placeholder="Kein Drucker"
                  showClear
                />
              </div>
            </div>
          </div>
          <p v-if="!cashRegistersLocal.length" class="muted">Noch keine Kassen.</p>
        </TabPanel>

        <TabPanel header="Gutscheine">
          <div class="section-toolbar">
            <Button label="Gutschein hinzufügen" type="button" class="primary-button" @click="addVoucher" />
          </div>
          <p v-if="!vouchersLocal.length" class="muted">Noch keine Gutschein-Typen.</p>
          <div v-for="(vd, vi) in vouchersLocal" :key="'vd-' + vi" class="config-card">
            <div class="config-card-header">
              <span>{{ vd.name || 'Unbenannter Gutschein' }}</span>
              <Button icon="pi pi-trash" text rounded type="button" severity="danger" @click="removeVoucher(vi)" />
            </div>
            <div class="form-field">
              <label>Name</label>
              <InputText v-model="vd.name" placeholder="z. B. 20.- Gutschein" />
            </div>
            <div class="form-field">
              <label>Art</label>
              <Select
                v-model="vd.kind"
                :options="voucherKindOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
            <div v-if="vd.kind === 'fixed_amount'" class="form-field">
              <label>Betrag ({{ currencyLabel }})</label>
              <InputNumber v-model="vd.value_amount" :min="0.01" :max="9999" :minFractionDigits="2" :maxFractionDigits="2" />
            </div>
            <template v-else>
              <div class="form-field">
                <label>Berechtigte Artikel</label>
                <MultiSelect
                  v-model="vd.allowed_article_ids"
                  :options="articleOptions"
                  optionLabel="name"
                  optionValue="value"
                  placeholder="Artikel wählen"
                  filter
                  display="chip"
                />
              </div>
              <div class="check-row">
                <Checkbox :inputId="'vadd-' + vi" v-model="vd.include_additions" :binary="true" />
                <label :for="'vadd-' + vi">Zusätze inklusive</label>
              </div>
            </template>
          </div>
        </TabPanel>

        <TabPanel header="App-Layouts">
          <div class="section-toolbar">
            <Button label="Layout hinzufügen" type="button" class="primary-button" @click="addLayout" />
          </div>
          <div v-for="(lo, li) in layoutsLocal" :key="'lo-' + li" class="config-card">
            <div class="config-card-header">
              <span>Layout {{ li + 1 }}</span>
              <div class="layout-header-actions">
                <Checkbox
                  :inputId="'def-' + li"
                  :binary="true"
                  :modelValue="lo.is_default"
                  @update:modelValue="(v) => onDefaultLayoutChange(li, v)"
                />
                <label :for="'def-' + li" class="inline-check">Standard</label>
                <Button icon="pi pi-trash" text rounded type="button" severity="danger" @click="removeLayout(li)" />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Name</label>
                <InputText v-model="lo.name" placeholder="optional" />
              </div>
              <div class="form-field">
                <label>Breite</label>
                <InputNumber v-model="lo.grid_width" :min="1" :max="64" />
              </div>
              <div class="form-field">
                <label>Höhe</label>
                <InputNumber v-model="lo.grid_height" :min="1" :max="64" />
              </div>
            </div>
            <p class="muted small">Zellen anklicken zum Bearbeiten.</p>
            <div class="layout-grid-wrap">
              <div
                class="layout-grid"
                :style="{
                  gridTemplateColumns: `repeat(${lo.grid_width}, minmax(0, 1fr))`,
                  gridTemplateRows: `repeat(${lo.grid_height}, minmax(2.5rem, auto))`,
                }"
              >
                <button
                  v-for="pos in gridPositions(lo)"
                  :key="li + '-' + pos.row + '-' + pos.col"
                  type="button"
                  class="grid-cell"
                  :style="{ background: displayCell(lo, pos.row, pos.col).color || '#eee' }"
                  @click="openCellDialog(li, pos.row, pos.col)"
                >
                  <span class="grid-cell-label">{{ displayCell(lo, pos.row, pos.col).label || '·' }}</span>
                  <span v-if="cellPreviewMeta(lo, pos.row, pos.col)" class="grid-cell-count">
                    {{ cellPreviewMeta(lo, pos.row, pos.col) }}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel header="Lagerartikel">
          <EventStockTab :event-id="eventId" :stations="stationsLocal" />
        </TabPanel>

        <TabPanel header="Umsatz">
          <EventSalesTab :event-id="eventId" />
        </TabPanel>

        <TabPanel header="Sammelrechnungen">
          <EventCollectiveBillsTab :event-id="eventId" />
        </TabPanel>
      </TabView>

      <div class="config-save">
        <Button label="Konfiguration speichern" class="primary-button" type="button" :disabled="saving" @click="saveConfiguration" />
      </div>
    </template>

    <Dialog v-model:visible="cellDialogVisible" header="Zelle bearbeiten" modal class="cell-dialog" :style="{ width: '32rem' }">
      <div class="form-field">
        <label>Bezeichnung</label>
        <InputText v-model="cellEdit.label" />
      </div>
      <div class="form-field">
        <label>Farbe</label>
        <ColorPicker v-model="cellColorHex" format="hex" />
      </div>
      <div class="form-field">
        <label>Betrags-Gutscheine (Layout-Zelle)</label>
        <MultiSelect
          v-model="cellEdit.voucher_definition_uuids"
          :options="fixedAmountVoucherOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Gutscheine wählen"
          display="chip"
          filter
          class="w-full"
        />
      </div>
      <div class="form-field">
        <label>Artikel (nur Stationen-Artikel)</label>
        <TreeSelect
          v-model="cellTreeSelection"
          :options="cellTreeNodes"
          selectionMode="checkbox"
          display="chip"
          placeholder="Artikel wählen"
          class="w-full"
          :loading="treeLoading"
          filter
        />
      </div>
      <template #footer>
        <Button label="Abbrechen" class="secondary-button" type="button" @click="cellDialogVisible = false" />
        <Button label="Übernehmen" class="primary-button" type="button" @click="applyCellDialog" />
      </template>
    </Dialog>

    <Dialog v-model:visible="showWaiterPick" header="Kellner übernehmen" modal :style="{ width: '32rem' }">
      <div class="form-field">
        <label>Kellner</label>
        <MultiSelect
          v-model="pickedWaiterIds"
          :options="waiterOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Kellner wählen"
          display="chip"
          filter
          class="w-full"
        />
      </div>
      <template #footer>
        <Button label="Abbrechen" class="secondary-button" type="button" @click="closeWaiterPick" />
        <Button
          label="Übernehmen"
          class="primary-button"
          type="button"
          :disabled="!pickedWaiterIds.length"
          @click="confirmPickWaiter"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import ColorPicker from 'primevue/colorpicker'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import TabPanel from 'primevue/tabpanel'
import TabView from 'primevue/tabview'
import TreeSelect from 'primevue/treeselect'
import { apiFetch } from '../api'
import EventStockTab from './EventStockTab.vue'
import EventSalesTab from './EventSalesTab.vue'
import EventCollectiveBillsTab from './EventCollectiveBillsTab.vue'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
  organisationId: {
    type: Number,
    default: null,
  },
})

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const configMessage = ref('')
const configMessageType = ref('')

const printerOptions = ref([])
const stationsLocal = ref([])
const waitersLocal = ref([])
const layoutsLocal = ref([])
const cashRegistersLocal = ref([])
const vouchersLocal = ref([])
const articlesRaw = ref([])
const currencyLabel = ref('CHF')

const voucherKindOptions = [
  { label: 'Betrags-Gutschein', value: 'fixed_amount' },
  { label: 'Artikel-Gutschein (nur Einlösung)', value: 'article_entitlement' },
]
const waitersOrg = ref([])

const cellDialogVisible = ref(false)
const cellEditLayoutIndex = ref(0)
const cellEditRow = ref(0)
const cellEditCol = ref(0)
const cellEdit = ref({
  label: '',
  color: '#eeeeee',
  article_ids: [],
  voucher_definition_uuid: null,
  voucher_definition_uuids: [],
})
const cellTreeNodes = ref([])
const cellTreeSelection = ref({})
const treeLoading = ref(false)

const showWaiterPick = ref(false)
const pickedWaiterIds = ref([])

let waiterKey = 0

const articleOptions = computed(() => {
  const oid = props.organisationId
  return articlesRaw.value
    .filter((a) => !a.is_addition && (oid == null || Number(a.organisation_id) === Number(oid)))
    .map((a) => ({
      name: a.name,
      value: a.id,
    }))
})

const waiterOptions = computed(() =>
  waitersOrg.value.map((w) => ({ label: w.name, value: w.id })),
)

const layoutOptions = computed(() =>
  layoutsLocal.value.map((lo, idx) => ({
    name: lo.name?.trim() || `Layout ${idx + 1}`,
    value: lo.uuid,
  })),
)

const fixedAmountVoucherOptions = computed(() =>
  vouchersLocal.value
    .filter((vd) => vd.kind === 'fixed_amount' && vd.uuid)
    .map((vd) => ({
      label: vd.name || 'Gutschein',
      value: vd.uuid,
    })),
)

function newUuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function normalizePickupPrefix(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3)
}

function gridPositions(lo) {
  const out = []
  for (let row = 0; row < lo.grid_height; row += 1) {
    for (let col = 0; col < lo.grid_width; col += 1) {
      out.push({ row, col })
    }
  }
  return out
}

function displayCell(lo, row, col) {
  const c = lo.cells.find((x) => x.row === row && x.col === col)
  return c || {
    row,
    col,
    label: '',
    color: '#eeeeee',
    article_ids: [],
    voucher_definition_uuid: null,
    voucher_definition_uuids: [],
  }
}

function cellVoucherUuids(c) {
  const list = c?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (c?.voucher_definition_uuid) return [String(c.voucher_definition_uuid)]
  return []
}

function cellPreviewMeta(lo, row, col) {
  const c = displayCell(lo, row, col)
  const vCount = cellVoucherUuids(c).length
  const aCount = c.article_ids?.length || 0
  const parts = []
  if (vCount) parts.push(`${vCount} Gutschein${vCount > 1 ? 'e' : ''}`)
  if (aCount) parts.push(`${aCount} Artikel`)
  return parts.join(' · ')
}

function addVoucher() {
  vouchersLocal.value.push({
    uuid: newUuid(),
    name: '',
    kind: 'fixed_amount',
    value_amount: 20,
    allowed_article_ids: [],
    include_additions: true,
  })
}

function removeVoucher(idx) {
  const removed = vouchersLocal.value[idx]
  vouchersLocal.value.splice(idx, 1)
  if (!removed?.uuid) return
  for (const lo of layoutsLocal.value) {
    for (const c of lo.cells || []) {
      const uuids = cellVoucherUuids(c).filter((u) => u !== removed.uuid)
      c.voucher_definition_uuids = uuids
      c.voucher_definition_uuid = uuids[0] || null
    }
  }
}

function hexToPicker(value) {
  if (!value) return 'eeeeee'
  return String(value).replace(/^#/, '')
}

function pickerToHex(value) {
  if (!value) return '#eeeeee'
  const v = String(value).replace(/^#/, '').trim()
  return v.length ? `#${v}` : '#eeeeee'
}

const cellColorHex = computed({
  get: () => hexToPicker(cellEdit.value.color),
  set: (v) => {
    cellEdit.value.color = pickerToHex(v)
  },
})

function ensureCell(lo, row, col) {
  let c = lo.cells.find((x) => x.row === row && x.col === col)
  if (!c) {
    c = {
      row,
      col,
      label: '',
      color: '#eeeeee',
      article_ids: [],
      voucher_definition_uuid: null,
      voucher_definition_uuids: [],
    }
    lo.cells.push(c)
  }
  return c
}

function articleIdsToTreeSelection(ids) {
  const sel = {}
  for (const id of ids || []) {
    sel[`art-${id}`] = { checked: true, partialChecked: false }
  }
  return sel
}

function treeSelectionToArticleIds(sel) {
  if (!sel || typeof sel !== 'object') return []
  return Object.entries(sel)
    .filter(([k, v]) => k.startsWith('art-') && v && v.checked)
    .map(([k]) => Number(k.replace(/^art-/, '')))
    .filter((n) => !Number.isNaN(n))
}

function ensureDefaultLayout() {
  if (!layoutsLocal.value.length) {
    layoutsLocal.value.push({
      uuid: newUuid(),
      name: 'Standard',
      is_default: true,
      grid_width: 4,
      grid_height: 4,
      cells: [],
    })
  }
}

function setOnlyDefault(idx) {
  layoutsLocal.value.forEach((lo, i) => {
    lo.is_default = i === idx
  })
}

function onDefaultLayoutChange(layoutIndex, checked) {
  if (checked) {
    setOnlyDefault(layoutIndex)
  } else {
    const lo = layoutsLocal.value[layoutIndex]
    if (lo) lo.is_default = false
    if (!layoutsLocal.value.some((l) => l.is_default)) {
      const first = layoutsLocal.value[0]
      if (first) first.is_default = true
    }
  }
}

function addStation() {
  stationsLocal.value.push({
    name: `Station ${stationsLocal.value.length + 1}`,
    printer_appliance_id: null,
    kitchen_monitor_enabled: false,
    article_ids: [],
  })
}

function removeStation(idx) {
  stationsLocal.value.splice(idx, 1)
}

function addWaiterRow() {
  waiterKey += 1
  waitersLocal.value.push({ _key: `nw-${waiterKey}`, name: '', pin: '0000', source_waiter_id: null })
}

function removeWaiter(row) {
  const ix = waitersLocal.value.indexOf(row)
  if (ix >= 0) waitersLocal.value.splice(ix, 1)
}

function addLayout() {
  layoutsLocal.value.push({
    uuid: newUuid(),
    name: `Layout ${layoutsLocal.value.length + 1}`,
    is_default: false,
    grid_width: 4,
    grid_height: 4,
    cells: [],
  })
}

function removeLayout(idx) {
  const removed = layoutsLocal.value[idx]
  layoutsLocal.value.splice(idx, 1)
  if (!layoutsLocal.value.some((l) => l.is_default) && layoutsLocal.value.length) {
    layoutsLocal.value[0].is_default = true
  }
  if (removed) {
    const fallback = layoutsLocal.value[0]?.uuid || ''
    cashRegistersLocal.value.forEach((reg) => {
      if (reg.layout_uuid === removed.uuid) reg.layout_uuid = fallback
    })
  }
}

function addCashRegister() {
  cashRegistersLocal.value.push({
    name: `Kasse ${cashRegistersLocal.value.length + 1}`,
    pickup_code_prefix: String.fromCharCode(65 + (cashRegistersLocal.value.length % 26)),
    pin: '0000',
    layout_uuid: layoutsLocal.value[0]?.uuid || '',
    receipt_printer_appliance_id: null,
  })
}

function removeCashRegister(idx) {
  cashRegistersLocal.value.splice(idx, 1)
}

async function loadConfiguration() {
  loading.value = true
  loadError.value = ''
  configMessage.value = ''
  try {
    const [cfgRes, artRes, wRes] = await Promise.all([
      apiFetch(`/events/${props.eventId}/configuration`),
      apiFetch('/articles/'),
      apiFetch('/waiters/'),
    ])
    if (!cfgRes.ok) throw new Error(await cfgRes.text())
    if (!artRes.ok) throw new Error('articles')
    if (!wRes.ok) throw new Error('waiters')
    const cfg = await cfgRes.json()
    articlesRaw.value = await artRes.json()
    waitersOrg.value = (await wRes.json()).filter(
      (w) => props.organisationId == null || Number(w.organisation_id) === Number(props.organisationId),
    )

    printerOptions.value = cfg.printer_options || []
    stationsLocal.value = (cfg.stations || []).map((s) => ({
      uuid: s.uuid ?? null,
      name: s.name,
      printer_appliance_id: s.printer_appliance_id,
      kitchen_monitor_enabled: !!s.kitchen_monitor_enabled,
      article_ids: [...(s.article_ids || [])],
    }))
    waiterKey = 0
    waitersLocal.value = (cfg.event_waiters || []).map((w) => {
      waiterKey += 1
      return {
        _key: `ew-${w.uuid}-${waiterKey}`,
        uuid: w.uuid ?? null,
        name: w.name,
        pin: w.pin,
        source_waiter_id: w.source_waiter_id,
      }
    })
    layoutsLocal.value = (cfg.app_layouts || []).map((lo) => ({
      uuid: lo.uuid || newUuid(),
      name: lo.name || '',
      is_default: !!lo.is_default,
      grid_width: lo.grid_width,
      grid_height: lo.grid_height,
      cells: (lo.cells || []).map((c) => ({
        row: c.row,
        col: c.col,
        label: c.label || '',
        color: c.color || '#eeeeee',
        article_ids: [...(c.article_ids || [])],
        voucher_definition_uuid: c.voucher_definition_uuid || null,
        voucher_definition_uuids: [...cellVoucherUuids(c)],
      })),
    }))
    ensureDefaultLayout()
    vouchersLocal.value = (cfg.voucher_definitions || []).map((vd) => ({
      uuid: vd.uuid ?? newUuid(),
      name: vd.name || '',
      kind: vd.kind || 'fixed_amount',
      value_amount: vd.value_cents != null ? vd.value_cents / 100 : 20,
      allowed_article_ids: [...(vd.allowed_article_ids || [])],
      include_additions: vd.include_additions !== false,
    }))
    cashRegistersLocal.value = (cfg.cash_registers || []).map((reg) => ({
      uuid: reg.uuid ?? null,
      name: reg.name || '',
      pickup_code_prefix: normalizePickupPrefix(reg.pickup_code_prefix || 'A'),
      pin: reg.pin || '0000',
      layout_uuid: reg.layout_uuid || layoutsLocal.value[0]?.uuid || '',
      receipt_printer_appliance_id: reg.receipt_printer_appliance_id ?? null,
    }))
  } catch (e) {
    loadError.value = 'Konfiguration konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function openCellDialog(layoutIndex, row, col) {
  cellEditLayoutIndex.value = layoutIndex
  cellEditRow.value = row
  cellEditCol.value = col
  const lo = layoutsLocal.value[layoutIndex]
  const c = ensureCell(lo, row, col)
  const vUuids = cellVoucherUuids(c)
  cellEdit.value = {
    label: c.label || '',
    color: c.color || '#eeeeee',
    article_ids: [...(c.article_ids || [])],
    voucher_definition_uuid: vUuids[0] || null,
    voucher_definition_uuids: [...vUuids],
  }
  cellTreeSelection.value = articleIdsToTreeSelection(c.article_ids)
  cellDialogVisible.value = true
  treeLoading.value = true
  cellTreeNodes.value = []
  try {
    const r = await apiFetch(`/events/${props.eventId}/station-article-tree`)
    if (r.ok) {
      const data = await r.json()
      cellTreeNodes.value = data.nodes || []
    }
  } finally {
    treeLoading.value = false
  }
}

function applyCellDialog() {
  const lo = layoutsLocal.value[cellEditLayoutIndex.value]
  const c = ensureCell(lo, cellEditRow.value, cellEditCol.value)
  c.label = cellEdit.value.label || ''
  c.color = cellEdit.value.color || '#eeeeee'
  const vUuids = [...(cellEdit.value.voucher_definition_uuids || [])]
  c.voucher_definition_uuids = vUuids
  c.voucher_definition_uuid = vUuids[0] || null
  c.article_ids = treeSelectionToArticleIds(cellTreeSelection.value)
  cellDialogVisible.value = false
}

function openWaiterPick() {
  pickedWaiterIds.value = []
  showWaiterPick.value = true
}

function closeWaiterPick() {
  showWaiterPick.value = false
  pickedWaiterIds.value = []
}

function confirmPickWaiter() {
  const existingSourceIds = new Set(
    waitersLocal.value
      .map((row) => row.source_waiter_id)
      .filter((id) => id != null),
  )
  for (const id of pickedWaiterIds.value) {
    if (existingSourceIds.has(id)) continue
    const w = waitersOrg.value.find((x) => x.id === id)
    if (!w) continue
    waiterKey += 1
    waitersLocal.value.push({
      _key: `pick-${waiterKey}`,
      name: w.name,
      pin: w.pin,
      source_waiter_id: w.id,
    })
    existingSourceIds.add(id)
  }
  closeWaiterPick()
}

function buildPutPayload() {
  ensureDefaultLayout()
  return {
    stations: stationsLocal.value.map((s) => {
      const row = {
        name: s.name,
        printer_appliance_id: s.printer_appliance_id ?? null,
        kitchen_monitor_enabled: !!s.kitchen_monitor_enabled,
        article_ids: Array.isArray(s.article_ids) ? s.article_ids : [],
      }
      if (s.uuid != null) row.uuid = s.uuid
      return row
    }),
    event_waiters: waitersLocal.value.map((w) => {
      const row = {
        name: w.name,
        pin: w.pin,
        source_waiter_id: w.source_waiter_id ?? null,
      }
      if (w.uuid != null) row.uuid = w.uuid
      return row
    }),
    app_layouts: layoutsLocal.value.map((lo) => ({
      uuid: lo.uuid,
      name: lo.name?.trim() || null,
      is_default: !!lo.is_default,
      grid_width: lo.grid_width,
      grid_height: lo.grid_height,
      cells: (lo.cells || []).map((c) => {
        const vUuids = cellVoucherUuids(c)
        return {
          row: c.row,
          col: c.col,
          label: c.label || '',
          color: c.color || '#eeeeee',
          article_ids: Array.isArray(c.article_ids) ? c.article_ids : [],
          voucher_definition_uuid: vUuids[0] || null,
          voucher_definition_uuids: vUuids,
        }
      }),
    })),
    voucher_definitions: vouchersLocal.value.map((vd) => {
      const row = {
        name: vd.name,
        kind: vd.kind,
        allowed_article_ids: Array.isArray(vd.allowed_article_ids) ? vd.allowed_article_ids : [],
        include_additions: !!vd.include_additions,
      }
      if (vd.uuid) row.uuid = vd.uuid
      if (vd.kind === 'fixed_amount') {
        row.value_cents = Math.round(Number(vd.value_amount || 0) * 100)
      }
      return row
    }),
    cash_registers: cashRegistersLocal.value.map((reg) => {
      const row = {
        name: reg.name,
        pickup_code_prefix: normalizePickupPrefix(reg.pickup_code_prefix || 'A'),
        pin: reg.pin || '0000',
        layout_uuid: reg.layout_uuid,
        receipt_printer_appliance_id: reg.receipt_printer_appliance_id ?? null,
      }
      if (reg.uuid != null) row.uuid = reg.uuid
      return row
    }),
  }
}

async function saveConfiguration() {
  configMessage.value = ''
  saving.value = true
  try {
    const response = await apiFetch(`/events/${props.eventId}/configuration`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPutPayload()),
    })
    if (!response.ok) {
      let detail = await response.text()
      try {
        const j = JSON.parse(detail)
        if (typeof j.detail === 'string') detail = j.detail
      } catch {
        /* ignore */
      }
      configMessage.value = detail || 'Speichern fehlgeschlagen.'
      configMessageType.value = 'error'
      return
    }
    const cfg = await response.json()
    printerOptions.value = cfg.printer_options || []
    configMessage.value = 'Konfiguration gespeichert.'
    configMessageType.value = 'success'
    await loadConfiguration()
  } catch {
    configMessage.value = 'Konfiguration konnte nicht gespeichert werden.'
    configMessageType.value = 'error'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.eventId,
  () => {
    if (props.eventId) loadConfiguration()
  },
  { immediate: true },
)
</script>

<style scoped>
.event-config {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--p-content-border-color);
}

.event-config.event-config--unified {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.muted {
  color: var(--p-text-muted-color);
}

.muted.small {
  font-size: 0.85rem;
  margin: 0.25rem 0 0.75rem;
}

.section-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.config-card {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  padding: 1rem;
  margin-bottom: 1rem;
}

.config-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.layout-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.inline-check {
  font-size: 0.875rem;
  font-weight: 500;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.25rem 0 0.9rem;
}

label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.layout-grid-wrap {
  overflow: auto;
  max-width: 100%;
}

.layout-grid {
  display: grid;
  gap: 4px;
  min-width: min-content;
}

.grid-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  cursor: pointer;
  padding: 0.35rem;
  min-height: 2.5rem;
  text-align: center;
}

.grid-cell-label {
  font-size: 0.75rem;
  color: var(--p-text-color);
  word-break: break-word;
}

.grid-cell-count {
  font-size: 0.65rem;
  color: var(--p-text-muted-color);
  line-height: 1.1;
}

.config-save {
  margin-top: 1.25rem;
}

.list-table.nested {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
}

.success,
.error {
  margin-bottom: 0.75rem;
}

:deep(.p-multiselect),
:deep(.p-select),
:deep(.p-inputtext),
:deep(.p-inputnumber),
:deep(.p-treeselect) {
  width: 100%;
}

.w-full {
  width: 100%;
}

@media (max-width: 992px) {
  .field-row {
    grid-template-columns: 1fr;
  }

  .config-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .layout-header-actions {
    flex-wrap: wrap;
    width: 100%;
  }

  .section-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .section-toolbar :deep(.p-button) {
    width: 100%;
  }

  .config-save :deep(.p-button) {
    width: 100%;
  }

  :deep(.p-tabview-nav) {
    flex-wrap: nowrap;
    overflow-x: auto;
  }
}
</style>
