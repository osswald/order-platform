<template>
  <div class="event-config" :class="{ 'event-config--unified': !!$slots.stammdaten }">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <p v-if="configMessage" :class="configMessageType">{{ configMessage }}</p>

      <EventConfigLayout
        :mobile="isMobile"
        v-model:active-tab="activeConfigTab"
        :sections="configSections"
      >
        <template v-if="$slots.stammdaten" #stammdaten>
          <slot name="stammdaten" />
        </template>
        <template #stationen>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addStation">Station hinzufügen</v-btn>
          </div>
          <div v-for="(st, idx) in stationsLocal" :key="'st-' + idx" class="config-card">
            <div class="config-card-header">
              <span>{{ st.name || 'Unbenannte Station' }}</span>
              <v-btn
                icon="mdi-delete"
                variant="text"
                color="error"
                type="button"
                aria-label="Entfernen"
                @click="removeStation(idx)"
              />
            </div>
            <div class="form-field">
              <label>Name</label>
              <v-text-field v-model="st.name" placeholder="z. B. Bar" density="compact" hide-details />
            </div>
            <div class="form-field">
              <label>Drucker</label>
              <v-select
                v-model="st.printer_appliance_id"
                :items="printerOptions"
                item-title="name"
                item-value="id"
                placeholder="Kein Drucker"
                clearable
                density="compact"
                hide-details
              />
            </div>
            <v-checkbox
              v-model="st.kitchen_monitor_enabled"
              label="Kitchen Monitor aktiv"
              hide-details
              density="compact"
            />
            <div class="form-field">
              <label>Artikel</label>
              <v-select
                v-model="st.article_ids"
                :items="articleOptions"
                item-title="name"
                item-value="value"
                placeholder="Artikel wählen"
                multiple
                chips
                closable-chips
                density="compact"
                hide-details
              />
            </div>
          </div>
          <p v-if="!stationsLocal.length" class="muted">Noch keine Stationen.</p>
        </template>

        <template #kellner>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addWaiterRow">Kellner hinzufügen</v-btn>
            <v-btn variant="outlined" type="button" @click="openWaiterPick">Aus Organisation übernehmen</v-btn>
          </div>
          <VqDataTable
            :items="waitersLocal"
            item-value="_key"
            :headers="waiterHeaders"
            class="vq-data-table nested"
            hide-default-footer
          >
            <template #item.name="{ item }">
              <v-text-field v-model="item.name" density="compact" hide-details />
            </template>
            <template #item.pin="{ item }">
              <v-text-field v-model="item.pin" density="compact" hide-details />
            </template>
            <template #item.actions="{ item }">
              <v-btn
                icon="mdi-delete"
                variant="text"
                color="error"
                type="button"
                @click="removeWaiter(item)"
              />
            </template>
          </VqDataTable>
        </template>

        <template v-if="cashRegistersEnabled" #kassen>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addCashRegister">Kasse hinzufügen</v-btn>
          </div>
          <div v-for="(reg, ri) in cashRegistersLocal" :key="'reg-' + ri" class="config-card">
            <div class="config-card-header">
              <span>{{ reg.name || 'Unbenannte Kasse' }}</span>
              <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeCashRegister(ri)" />
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Name</label>
                <v-text-field v-model="reg.name" placeholder="z. B. Hauptkasse" density="compact" hide-details />
              </div>
              <div class="form-field">
                <label>Pickup-Code Buchstaben</label>
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
                <label>PIN</label>
                <v-text-field v-model="reg.pin" maxlength="4" placeholder="0000" density="compact" hide-details />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Layout</label>
                <v-select
                  v-model="reg.layout_uuid"
                  :items="layoutOptions"
                  item-title="name"
                  item-value="value"
                  placeholder="Layout wählen"
                  density="compact"
                  hide-details
                />
              </div>
              <div class="form-field">
                <label>Kundendrucker</label>
                <v-select
                  v-model="reg.receipt_printer_appliance_id"
                  :items="printerOptions"
                  item-title="name"
                  item-value="id"
                  placeholder="Kein Drucker"
                  clearable
                  density="compact"
                  hide-details
                />
              </div>
            </div>
          </div>
          <p v-if="!cashRegistersLocal.length" class="muted">Noch keine Kassen.</p>
        </template>

        <template v-if="vouchersEnabled" #gutscheine>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addVoucher">Gutschein hinzufügen</v-btn>
          </div>
          <p v-if="!vouchersLocal.length" class="muted">Noch keine Gutschein-Typen.</p>
          <div v-for="(vd, vi) in vouchersLocal" :key="'vd-' + vi" class="config-card">
            <div class="config-card-header">
              <span>{{ vd.name || 'Unbenannter Gutschein' }}</span>
              <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeVoucher(vi)" />
            </div>
            <div class="form-field">
              <label>Name</label>
              <v-text-field v-model="vd.name" placeholder="z. B. 20.- Gutschein" density="compact" hide-details />
            </div>
            <div class="form-field">
              <label>Art</label>
              <v-select
                v-model="vd.kind"
                :items="voucherKindOptions"
                item-title="label"
                item-value="value"
                density="compact"
                hide-details
              />
            </div>
            <div v-if="vd.kind === 'fixed_amount'" class="form-field">
              <label>Betrag ({{ currencyLabel }})</label>
              <v-number-input
                v-model="vd.value_amount"
                :min="0.01"
                :max="9999"
                :step="0.01"
                control-variant="stacked"
                density="compact"
                hide-details
              />
            </div>
            <template v-else>
              <div class="form-field">
                <label>Berechtigte Artikel</label>
                <v-select
                  v-model="vd.allowed_article_ids"
                  :items="articleOptions"
                  item-title="name"
                  item-value="value"
                  placeholder="Artikel wählen"
                  multiple
                  chips
                  closable-chips
                  density="compact"
                  hide-details
                />
              </div>
              <v-checkbox
                v-model="vd.include_additions"
                label="Zusätze inklusive"
                hide-details
                density="compact"
              />
            </template>
          </div>
        </template>

        <template #layouts>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addLayout">Layout hinzufügen</v-btn>
          </div>
          <div v-for="(lo, li) in layoutsLocal" :key="'lo-' + li" class="config-card">
            <div class="config-card-header">
              <span>Layout {{ li + 1 }}</span>
              <div class="layout-header-actions">
                <v-checkbox
                  :model-value="lo.is_default"
                  label="Standard"
                  hide-details
                  density="compact"
                  @update:model-value="(v) => onDefaultLayoutChange(li, v)"
                />
                <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeLayout(li)" />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>Name</label>
                <v-text-field v-model="lo.name" placeholder="optional" density="compact" hide-details />
              </div>
              <div class="form-field">
                <label>Breite</label>
                <v-number-input
                  v-model="lo.grid_width"
                  :min="1"
                  :max="64"
                  control-variant="stacked"
                  density="compact"
                  hide-details
                />
              </div>
              <div class="form-field">
                <label>Höhe</label>
                <v-number-input
                  v-model="lo.grid_height"
                  :min="1"
                  :max="64"
                  control-variant="stacked"
                  density="compact"
                  hide-details
                />
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
        </template>

        <template #belege>
          <ReceiptPrintingSection
            :api-base-path="`/events/${eventId}`"
            :entity-id="eventId"
            is-event
            title="Beleg-Druck"
            hint="Gilt für Station- und Kundenbelege dieser Veranstaltung (Pi-Sync)."
          />
        </template>

        <template #lager>
          <EventStockTab :event-id="eventId" :stations="stationsLocal" />
        </template>

        <template v-if="showOperationalTabs" #umsatz>
          <EventSalesTab :event-id="eventId" />
        </template>

        <template v-if="showOperationalTabs" #sammelrechnungen>
          <EventCollectiveBillsTab :event-id="eventId" />
        </template>

        <template v-if="showTransactionsTab" #transaktionen>
          <EventTransactionsTab :event-id="eventId" />
        </template>
      </EventConfigLayout>

      <div class="config-save">
        <v-btn color="primary" type="button" :disabled="saving" @click="saveConfiguration">
          Konfiguration speichern
        </v-btn>
      </div>
    </template>

    <v-dialog v-model="cellDialogVisible" max-width="32rem" class="cell-dialog">
      <v-card>
        <v-card-title>Zelle bearbeiten</v-card-title>
        <v-card-text>
          <div class="form-field">
            <label>Bezeichnung</label>
            <v-text-field v-model="cellEdit.label" density="compact" hide-details />
          </div>
          <div class="form-field">
            <label>Farbe</label>
            <v-color-picker v-model="cellEdit.color" mode="hex" hide-inputs />
          </div>
          <div v-if="vouchersEnabled" class="form-field">
            <label>Betrags-Gutscheine (Layout-Zelle)</label>
            <v-select
              v-model="cellEdit.voucher_definition_uuids"
              :items="fixedAmountVoucherOptions"
              item-title="label"
              item-value="value"
              placeholder="Gutscheine wählen"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </div>
          <div class="form-field">
            <label>Artikel (nur Stationen-Artikel)</label>
            <v-text-field
              v-model="cellTreeFilter"
              placeholder="Artikel filtern…"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
              class="tree-filter"
            />
            <v-progress-linear v-if="treeLoading" indeterminate color="primary" class="tree-loading" />
            <v-treeview
              v-else
              v-model:selected="cellTreeSelection"
              :items="filteredCellTreeItems"
              item-value="key"
              item-title="title"
              item-children="children"
              selectable
              select-strategy="leaf"
              open-all
              density="compact"
            />
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer />
          <v-btn variant="outlined" type="button" @click="cellDialogVisible = false">Abbrechen</v-btn>
          <v-btn color="primary" type="button" @click="applyCellDialog">Übernehmen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showWaiterPick" max-width="32rem">
      <v-card>
        <v-card-title>Kellner übernehmen</v-card-title>
        <v-card-text>
          <div class="form-field">
            <label>Kellner</label>
            <v-select
              v-model="pickedWaiterIds"
              :items="waiterOptions"
              item-title="label"
              item-value="value"
              placeholder="Kellner wählen"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer />
          <v-btn variant="outlined" type="button" @click="closeWaiterPick">Abbrechen</v-btn>
          <v-btn
            color="primary"
            type="button"
            :disabled="!pickedWaiterIds.length"
            @click="confirmPickWaiter"
          >
            Übernehmen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, useSlots } from 'vue'
import { apiFetch } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'
import EventConfigLayout from './EventConfigLayout.vue'
import EventStockTab from './EventStockTab.vue'
import EventSalesTab from './EventSalesTab.vue'
import EventCollectiveBillsTab from './EventCollectiveBillsTab.vue'
import EventTransactionsTab from './EventTransactionsTab.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
  organisationId: {
    type: Number,
    default: null,
  },
  eventStatus: {
    type: String,
    default: 'config',
  },
  cashRegistersEnabled: {
    type: Boolean,
    default: false,
  },
  vouchersEnabled: {
    type: Boolean,
    default: false,
  },
})

const slots = useSlots()
const { matches: isMobile } = useBreakpoint(768)
const showOperationalTabs = computed(() => props.eventStatus !== 'config')
const showTransactionsTab = computed(() =>
  ['test', 'prod', 'archive'].includes(String(props.eventStatus || '').toLowerCase()),
)

const waiterHeaders = [
  { title: 'Name', key: 'name', sortable: false },
  { title: 'PIN', key: 'pin', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end', width: '4rem' },
]

const configSections = computed(() => {
  const list = []
  if (slots.stammdaten) {
    list.push({ id: 'stammdaten', title: 'Stammdaten', defaultOpen: true })
  }
  list.push({
    id: 'stationen',
    title: 'Stationen',
    defaultOpen: !slots.stammdaten,
  })
  list.push({ id: 'kellner', title: 'Event-Kellner' })
  if (props.cashRegistersEnabled) {
    list.push({ id: 'kassen', title: 'Kassen' })
  }
  if (props.vouchersEnabled) {
    list.push({ id: 'gutscheine', title: 'Gutscheine' })
  }
  list.push({ id: 'layouts', title: 'App-Layouts' })
  list.push({ id: 'belege', title: 'Belege' })
  list.push({ id: 'lager', title: 'Lagerartikel' })
  if (showOperationalTabs.value) {
    list.push({ id: 'umsatz', title: 'Umsatz (neu)' })
    list.push({ id: 'sammelrechnungen', title: 'Sammelrechnungen' })
  }
  if (showTransactionsTab.value) {
    list.push({ id: 'transaktionen', title: 'Transaktionen' })
  }
  return list
})

const activeConfigTab = ref('stammdaten')

watch(
  configSections,
  (sections) => {
    if (!sections.some((s) => s.id === activeConfigTab.value)) {
      activeConfigTab.value = sections[0]?.id ?? 'stationen'
    }
  },
  { immediate: true },
)

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
const cellTreeNodesRaw = ref([])
const cellTreeSelection = ref([])
const cellTreeFilter = ref('')
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

const cellTreeItems = computed(() => mapTreeNodes(cellTreeNodesRaw.value))

const filteredCellTreeItems = computed(() => {
  const q = cellTreeFilter.value.trim().toLowerCase()
  if (!q) return cellTreeItems.value
  return filterTreeNodes(cellTreeItems.value, q)
})

function mapTreeNodes(nodes) {
  return (nodes || []).map((n) => ({
    key: n.key,
    title: n.label,
    children: n.children?.length ? mapTreeNodes(n.children) : undefined,
  }))
}

function filterTreeNodes(nodes, query) {
  const out = []
  for (const node of nodes) {
    if (node.children?.length) {
      const filteredChildren = filterTreeNodes(node.children, query)
      if (filteredChildren.length) {
        out.push({ ...node, children: filteredChildren })
      } else if (node.title.toLowerCase().includes(query)) {
        out.push({ ...node })
      }
    } else if (node.title.toLowerCase().includes(query)) {
      out.push({ ...node })
    }
  }
  return out
}

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

/** Map article IDs to v-treeview selected keys (art-{id}). */
function articleIdsToTreeSelection(ids) {
  return (ids || []).map((id) => `art-${id}`)
}

/** Extract article IDs from v-treeview selected keys. */
function treeSelectionToArticleIds(sel) {
  if (!Array.isArray(sel)) return []
  return sel
    .filter((k) => typeof k === 'string' && k.startsWith('art-'))
    .map((k) => Number(k.replace(/^art-/, '')))
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
  } catch {
    loadError.value = 'Konfiguration konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function openCellDialog(layoutIndex, row, col) {
  cellEditLayoutIndex.value = layoutIndex
  cellEditRow.value = row
  cellEditCol.value = col
  cellTreeFilter.value = ''
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
  cellTreeNodesRaw.value = []
  try {
    const r = await apiFetch(`/events/${props.eventId}/station-article-tree`)
    if (r.ok) {
      const data = await r.json()
      cellTreeNodesRaw.value = data.nodes || []
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
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.event-config.event-config--unified {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.muted {
  opacity: 0.65;
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
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  background: rgba(var(--v-theme-on-surface), 0.02);
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

label {
  font-size: 0.875rem;
  font-weight: 600;
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
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  cursor: pointer;
  padding: 0.35rem;
  min-height: 2.5rem;
  text-align: center;
}

.grid-cell-label {
  font-size: 0.75rem;
  word-break: break-word;
}

.grid-cell-count {
  font-size: 0.65rem;
  opacity: 0.65;
  line-height: 1.1;
}

.config-save {
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  display: flex;
  justify-content: flex-end;
}

.vq-data-table.nested {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.success,
.error {
  margin-bottom: 0.75rem;
}

.tree-filter {
  margin-bottom: 0.5rem;
}

.tree-loading {
  margin-top: 0.5rem;
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
}
</style>
