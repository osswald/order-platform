<template>
  <div class="event-config" :class="{ 'event-config--unified': !!$slots.stammdaten }">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else>
      <p class="form-required-legend config-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>
      <SectionNavLayout
        :mobile="isMobile"
        v-model:active-tab="activeConfigTab"
        :sections="configSections"
        :nav-aria-label="$t('events.configNavAria')"
      >
        <template v-if="$slots.stammdaten" #stammdaten>
          <slot name="stammdaten" />
        </template>
        <template #stationen>
          <EventConfigStationsSection
            v-model="stationsLocal"
            :catalog-loading="catalogLoading"
            :catalog-error="catalogError"
            :printer-options="printerOptions"
            :article-options="articleOptions"
            :alternative-printers-enabled="alternativePrintersEnabled"
            :printer-rule-type-options="printerRuleTypeOptions"
          />
        </template>

        <template v-if="kitchenMonitorsEnabled" #kitchen-monitors>
          <EventConfigKitchenMonitorsSection
            v-model="kitchenMonitorsLocal"
            :printer-options="printerOptions"
            :kitchen-monitor-printer-options="kitchenMonitorPrinterOptions"
          />
        </template>

        <template #kellner>
          <EventConfigWaitersSection
            v-model="waitersLocal"
            :catalog-loading="catalogLoading"
            :accounts-enabled="accountsEnabled"
            @import-from-org="openWaiterPick"
          />
        </template>

        <template v-if="cashRegistersEnabled" #kassen>
          <EventConfigCashRegistersSection
            v-model="cashRegistersLocal"
            :layout-options="layoutOptions"
            :default-layout-uuid="layoutsLocal[0]?.uuid || ''"
            :printer-options="printerOptions"
            :accounts-enabled="accountsEnabled"
          />
        </template>

        <template v-if="vouchersEnabled" #gutscheine>
          <EventConfigVouchersSection
            v-model="vouchersLocal"
            :article-options="articleOptions"
            :catalog-loading="catalogLoading"
            :currency-label="currencyLabel"
            :voucher-kind-options="voucherKindOptions"
            @voucher-removed="onVoucherRemoved"
          />
        </template>

        <template #layouts>
          <EventConfigLayoutsSection
            ref="layoutsSectionRef"
            v-model="layoutsLocal"
            v-model:cell-dialog-open="cellDialogOpen"
            :event-id="eventId"
            :vouchers-enabled="vouchersEnabled"
            :voucher-definitions="vouchersLocal"
            @layout-removed="onLayoutRemoved"
          />
        </template>

        <template #belege>
          <ReceiptPrintingSection
            :api-base-path="`/events/${eventId}`"
            :entity-id="eventId"
            is-event
            :title="$t('events.config.receiptPrintTitle')"
            :hint="$t('events.config.receiptPrintHint')"
            @status-change="onReceiptStatusChange"
          />
        </template>

        <template #lager>
          <EventStockTab
            :event-id="eventId"
            :stations="stationsLocal"
            @status-change="onStockStatusChange"
          />
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

        <template v-if="showTransactionsTab && shiftSettlementEnabled" #schichten>
          <EventCashSessionsTab :event-id="eventId" />
        </template>

        <template v-if="showBookkeepingTab" #buchhaltung>
          <EventBookkeepingTab :event-id="eventId" :currency="organisationCurrency" />
        </template>
      </SectionNavLayout>

      <EventSaveStatusBar
        :configuration-status="configAutosaveStatus"
        :receipt-status="receiptSaveStatus"
        :stock-status="stockSaveStatus"
        :stammdaten-dirty="stammdatenDirty"
        :configuration-error="configAutosaveError"
        :receipt-error="receiptSaveError"
        :stock-error="stockSaveError"
      />
    </template>

    <EventConfigWaiterImportDialog
      v-model="showWaiterPick"
      v-model:picked-waiter-ids="pickedWaiterIds"
      :catalog-loading="catalogLoading"
      :catalog-error="catalogError"
      :waiter-options="waiterOptions"
      @confirm="confirmPickWaiter"
      @cancel="closeWaiterPick"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, useSlots, onMounted, onBeforeUnmount, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { useBreakpoint } from '../composables/useBreakpoint'
import { MOBILE_BREAKPOINT } from '../constants/layout'
import { useEventConfigurationAutosave } from '../composables/useEventConfigurationAutosave'
import { loadOrgCatalog } from '../composables/useOrgCatalog'
import SectionNavLayout from './SectionNavLayout.vue'
import EventSaveStatusBar from './EventSaveStatusBar.vue'
import EventConfigStationsSection from './EventConfigStationsSection.vue'
import EventConfigKitchenMonitorsSection from './EventConfigKitchenMonitorsSection.vue'
import EventConfigWaitersSection from './EventConfigWaitersSection.vue'
import EventConfigCashRegistersSection from './EventConfigCashRegistersSection.vue'
import EventConfigVouchersSection from './EventConfigVouchersSection.vue'
import EventConfigLayoutsSection from './EventConfigLayoutsSection.vue'
import EventConfigWaiterImportDialog from './EventConfigWaiterImportDialog.vue'
import EventStockTab from './EventStockTab.vue'
import EventSalesTab from './EventSalesTab.vue'
import EventCollectiveBillsTab from './EventCollectiveBillsTab.vue'
import EventTransactionsTab from './EventTransactionsTab.vue'
import EventCashSessionsTab from './EventCashSessionsTab.vue'
import EventBookkeepingTab from './EventBookkeepingTab.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import { organisationAccountsEnabled } from '../utils/orgScope.js'
import { SESSION_CONTEXT_KEY } from '../sessionContext'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
  organisationId: {
    type: Number,
    default: null,
  },
  organisationCurrency: {
    type: String,
    default: 'EUR',
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
  shiftSettlementEnabled: {
    type: Boolean,
    default: false,
  },
  alternativePrintersEnabled: {
    type: Boolean,
    default: false,
  },
  kitchenMonitorsEnabled: {
    type: Boolean,
    default: false,
  },
  stammdatenDirty: {
    type: Boolean,
    default: false,
  },
})

const slots = useSlots()
const { t } = useI18n()
const sessionContext = inject(SESSION_CONTEXT_KEY, null)
const { matches: isMobile } = useBreakpoint(MOBILE_BREAKPOINT)
const showOperationalTabs = computed(() => props.eventStatus !== 'config')
const showTransactionsTab = computed(() =>
  ['test', 'prod', 'archive'].includes(String(props.eventStatus || '').toLowerCase()),
)

const accountsEnabled = computed(() =>
  organisationAccountsEnabled(sessionContext?.accessibleOrganisations?.value || [], props.organisationId),
)
const showBookkeepingTab = computed(() => showOperationalTabs.value && accountsEnabled.value)

const configSections = computed(() => {
  const list = []
  if (slots.stammdaten) {
    list.push({ id: 'stammdaten', title: t('events.config.sectionStammdaten'), defaultOpen: true })
  }
  list.push({
    id: 'stationen',
    title: t('events.config.sectionStationen'),
    defaultOpen: !slots.stammdaten,
  })
  if (props.kitchenMonitorsEnabled) {
    list.push({ id: 'kitchen-monitors', title: t('events.config.sectionKitchenMonitors') })
  }
  list.push({ id: 'kellner', title: t('events.config.sectionKellner') })
  if (props.cashRegistersEnabled) {
    list.push({ id: 'kassen', title: t('events.config.sectionKassen') })
  }
  if (props.vouchersEnabled) {
    list.push({ id: 'gutscheine', title: t('events.config.sectionGutscheine') })
  }
  list.push({ id: 'layouts', title: t('events.config.sectionLayouts') })
  list.push({ id: 'belege', title: t('events.config.sectionBelege') })
  list.push({ id: 'lager', title: t('events.config.sectionLager') })
  if (showOperationalTabs.value) {
    list.push({ id: 'umsatz', title: t('events.config.sectionUmsatz') })
    list.push({ id: 'sammelrechnungen', title: t('events.config.sectionSammelrechnungen') })
  }
  if (showTransactionsTab.value) {
    list.push({ id: 'transaktionen', title: t('events.config.sectionTransaktionen') })
  }
  if (showTransactionsTab.value && props.shiftSettlementEnabled) {
    list.push({ id: 'schichten', title: t('events.config.sectionSchichten') })
  }
  if (showBookkeepingTab.value) {
    list.push({ id: 'buchhaltung', title: t('events.config.sectionBuchhaltung') })
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
const catalogLoading = ref(false)
const catalogError = ref('')

const layoutsSectionRef = ref(null)
const cellDialogOpen = ref(false)

const receiptSaveStatus = ref('idle')
const receiptSaveError = ref('')
const stockSaveStatus = ref('idle')
const stockSaveError = ref('')

function onReceiptStatusChange({ status, errorMessage }) {
  receiptSaveStatus.value = status || 'idle'
  receiptSaveError.value = errorMessage || ''
}

function onStockStatusChange({ status, errorMessage }) {
  stockSaveStatus.value = status || 'idle'
  stockSaveError.value = errorMessage || ''
}

const printerOptions = ref([])
const stationsLocal = ref([])
const kitchenMonitorsLocal = ref([])
const waitersLocal = ref([])
const layoutsLocal = ref([])
const cashRegistersLocal = ref([])
const vouchersLocal = ref([])
const articlesRaw = ref([])
const currencyLabel = computed(() => props.organisationCurrency || 'EUR')

const voucherKindOptions = computed(() => [
  { label: t('events.config.voucherKindFixedAmount'), value: 'fixed_amount' },
  { label: t('events.config.voucherKindArticleEntitlement'), value: 'article_entitlement' },
])
const printerRuleTypeOptions = computed(() => [
  { label: t('events.config.ruleTypeTableRange'), value: 'table_range' },
  { label: t('events.config.ruleTypePickupPrefix'), value: 'pickup_prefix' },
])
const waitersOrg = ref([])

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

const kitchenMonitorPrinterOptions = computed(() => {
  const ids = new Set()
  for (const st of stationsLocal.value) {
    if (st.printer_appliance_id != null) ids.add(Number(st.printer_appliance_id))
    for (const rule of st.printer_rules || []) {
      if (rule.printer_appliance_id != null) ids.add(Number(rule.printer_appliance_id))
    }
  }
  for (const reg of cashRegistersLocal.value) {
    if (reg.receipt_printer_appliance_id != null) ids.add(Number(reg.receipt_printer_appliance_id))
  }
  return printerOptions.value.filter((opt) => ids.has(Number(opt.id)))
})

const waiterOptions = computed(() =>
  waitersOrg.value.map((w) => ({ label: w.name, value: w.id })),
)

const layoutOptions = computed(() =>
  layoutsLocal.value.map((lo, idx) => ({
    name: lo.name?.trim() || t('events.config.layoutN', { n: idx + 1 }),
    value: lo.uuid,
  })),
)

function cellVoucherUuids(c) {
  const list = c?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (c?.voucher_definition_uuid) return [String(c.voucher_definition_uuid)]
  return []
}

function isCellInGrid(c, width, height) {
  return c.row >= 0 && c.col >= 0 && c.row < height && c.col < width
}

function onVoucherRemoved(uuid) {
  for (const lo of layoutsLocal.value) {
    for (const c of lo.cells || []) {
      const uuids = cellVoucherUuids(c).filter((u) => u !== uuid)
      c.voucher_definition_uuids = uuids
      c.voucher_definition_uuid = uuids[0] || null
    }
  }
}

function onLayoutRemoved({ removedUuid, fallbackUuid }) {
  cashRegistersLocal.value.forEach((reg) => {
    if (reg.layout_uuid === removedUuid) reg.layout_uuid = fallbackUuid
  })
}

function newUuid() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function normalizePickupPrefix(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3)
}

function configurationValidationError() {
  for (const s of stationsLocal.value) {
    if (!(s.name || '').trim()) {
      return t('events.config.validationStationName')
    }
  }
  for (const w of waitersLocal.value) {
    if (!(w.name || '').trim()) {
      return t('events.config.validationWaiterName')
    }
    if (!(String(w.pin || '')).trim()) {
      return t('events.config.validationWaiterPin')
    }
  }
  if (props.cashRegistersEnabled) {
    for (const reg of cashRegistersLocal.value) {
      if (!(reg.name || '').trim()) {
        return t('events.config.validationCashRegisterName')
      }
    }
  }
  if (props.vouchersEnabled) {
    for (const vd of vouchersLocal.value) {
      if (!(vd.name || '').trim()) {
        return t('events.config.validationVoucherName')
      }
    }
  }
  return null
}

function mapLayoutCells(cells) {
  return (cells || []).map((c) => ({
    row: c.row,
    col: c.col,
    label: c.label || '',
    color: c.color || '#eeeeee',
    article_ids: [...(c.article_ids || [])],
    voucher_definition_uuid: c.voucher_definition_uuid || null,
    voucher_definition_uuids: [...cellVoucherUuids(c)],
  }))
}

function mapLayoutFromApi(lo) {
  return {
    uuid: lo.uuid || newUuid(),
    name: lo.name || '',
    is_default: !!lo.is_default,
    grid_width: lo.grid_width,
    grid_height: lo.grid_height,
    cells: mapLayoutCells(lo.cells),
  }
}

function applyConfigurationFromResponse(cfg, { includeLayoutCells = true } = {}) {
  printerOptions.value = cfg.printer_options || []
  stationsLocal.value = (cfg.stations || []).map((s) => ({
    uuid: s.uuid ?? null,
    name: s.name,
    printer_appliance_id: s.printer_appliance_id,
    printer_rules: (s.printer_rules || []).map((rule, ruleIdx) => ({
      sort_order: rule.sort_order ?? ruleIdx,
      rule_type: rule.rule_type || 'table_range',
      table_from: rule.table_from ?? null,
      table_to: rule.table_to ?? null,
      pickup_prefix: rule.pickup_prefix ? normalizePickupPrefix(rule.pickup_prefix) : '',
      printer_appliance_id: rule.printer_appliance_id ?? null,
    })),
    article_ids: [...(s.article_ids || [])],
  }))
  kitchenMonitorsLocal.value = (cfg.kitchen_monitors || []).map((row, idx) => ({
    printer_appliance_id: row.printer_appliance_id ?? null,
    sort_order: row.sort_order ?? idx,
    label: row.label || '',
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
      subsidiary_code: w.subsidiary_code || '',
    }
  })
  layoutsLocal.value = (cfg.app_layouts || []).map((lo) => mapLayoutFromApi(lo))
  layoutsSectionRef.value?.ensureDefaultLayout()
  if (!includeLayoutCells) {
    layoutsSectionRef.value?.resetLayoutCellsState()
  }
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
    subsidiary_code: reg.subsidiary_code || '',
  }))
}

async function loadCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const result = await loadOrgCatalog(props.organisationId)
    articlesRaw.value = result.articles
    waitersOrg.value = result.waiters
    if (result.fromCache && result.refreshPromise) {
      catalogLoading.value = false
      const orgId = props.organisationId
      result.refreshPromise.then((data) => {
        if (!data || props.organisationId !== orgId) return
        articlesRaw.value = data.articles
        waitersOrg.value = data.waiters
      })
      return
    }
  } catch {
    catalogError.value = t('events.config.catalogLoadFailed')
    articlesRaw.value = []
    waitersOrg.value = []
  } finally {
    catalogLoading.value = false
  }
}

async function loadConfiguration() {
  loading.value = true
  loadError.value = ''
  catalogError.value = ''
  layoutsSectionRef.value?.resetLayoutCellsState()
  articlesRaw.value = []
  waitersOrg.value = []
  if (resetConfigSnapshot) resetConfigSnapshot()
  try {
    applyConfigurationFromResponse(
      await apiJson(`/events/${props.eventId}/configuration?fields=summary`),
      { includeLayoutCells: false },
    )
  } catch {
    loadError.value = t('events.config.loadFailed')
  } finally {
    loading.value = false
    if (!loadError.value && markConfigSaved) {
      markConfigSaved()
    }
  }
  if (!loadError.value) {
    void loadCatalog()
  }
}

function openWaiterPick() {
  pickedWaiterIds.value = []
  showWaiterPick.value = true
}

function closeWaiterPick() {
  showWaiterPick.value = false
  pickedWaiterIds.value = []
}

function confirmPickWaiter(ids = pickedWaiterIds.value) {
  const existingSourceIds = new Set(
    waitersLocal.value
      .map((row) => row.source_waiter_id)
      .filter((id) => id != null),
  )
  for (const id of ids) {
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
  layoutsSectionRef.value?.ensureDefaultLayout()
  return {
    stations: stationsLocal.value.map((s) => {
      const row = {
        name: s.name,
        printer_appliance_id: s.printer_appliance_id ?? null,
        article_ids: Array.isArray(s.article_ids) ? s.article_ids : [],
        printer_rules: (s.printer_rules || []).map((rule, ruleIdx) => ({
          sort_order: ruleIdx,
          rule_type: rule.rule_type,
          table_from: rule.rule_type === 'table_range' ? Number(rule.table_from) || null : null,
          table_to: rule.rule_type === 'table_range' ? Number(rule.table_to) || null : null,
          pickup_prefix:
            rule.rule_type === 'pickup_prefix'
              ? normalizePickupPrefix(rule.pickup_prefix || '')
              : null,
          printer_appliance_id: rule.printer_appliance_id ?? null,
        })),
      }
      if (s.uuid != null) row.uuid = s.uuid
      return row
    }),
    event_waiters: waitersLocal.value.map((w) => {
      const row = {
        name: w.name,
        pin: w.pin,
        source_waiter_id: w.source_waiter_id ?? null,
        subsidiary_code: (w.subsidiary_code || '').trim() || null,
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
      cells: (lo.cells || [])
        .filter((c) => isCellInGrid(c, lo.grid_width, lo.grid_height))
        .map((c) => {
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
        subsidiary_code: (reg.subsidiary_code || '').trim() || null,
      }
      if (reg.uuid != null) row.uuid = reg.uuid
      return row
    }),
    kitchen_monitors: kitchenMonitorsLocal.value.map((row, idx) => ({
      printer_appliance_id: Number(row.printer_appliance_id),
      sort_order: idx,
      label: (row.label || '').trim() || null,
    })),
  }
}

async function persistConfiguration() {
  const validationErr = configurationValidationError()
  if (validationErr) {
    setConfigAutosaveError(validationErr)
    return false
  }
  try {
    const cfg = await apiJson(`/events/${props.eventId}/configuration`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPutPayload()),
    })
    printerOptions.value = cfg.printer_options || []
    return true
  } catch (err) {
    setConfigAutosaveError(err.message || t('events.config.saveFailed'))
    return false
  }
}

const configWatchSource = computed(() => ({
  stations: stationsLocal.value,
  waiters: waitersLocal.value,
  layouts: layoutsLocal.value,
  vouchers: vouchersLocal.value,
  cashRegisters: cashRegistersLocal.value,
}))

const configAutosaveEnabled = computed(
  () => !loading.value && !loadError.value && !cellDialogOpen.value,
)

const {
  status: configAutosaveStatus,
  errorMessage: configAutosaveError,
  markSaved: markConfigSaved,
  resetSnapshot: resetConfigSnapshot,
  setError: setConfigAutosaveError,
  isDirty: configIsDirty,
} = useEventConfigurationAutosave({
  getSnapshot: buildPutPayload,
  saveFn: persistConfiguration,
  watchSource: configWatchSource,
  enabled: configAutosaveEnabled,
  validate: configurationValidationError,
})

const hasUnsavedChanges = computed(
  () =>
    props.stammdatenDirty ||
    configIsDirty.value ||
    configAutosaveStatus.value === 'dirty' ||
    configAutosaveStatus.value === 'saving' ||
    receiptSaveStatus.value === 'dirty' ||
    receiptSaveStatus.value === 'saving' ||
    stockSaveStatus.value === 'dirty' ||
    stockSaveStatus.value === 'saving',
)

function onBeforeUnload(event) {
  if (!hasUnsavedChanges.value) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
})

watch(
  () => props.eventId,
  () => {
    if (props.eventId) loadConfiguration()
  },
  { immediate: true },
)

watch(activeConfigTab, (tab) => {
  if (tab === 'layouts') layoutsSectionRef.value?.loadLayoutCells()
})

defineExpose({
  loadConfiguration,
})
</script>

<style scoped>
.event-config {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.catalog-loading-hint {
  margin: 0 0 0.75rem;
}

.event-config.event-config--unified {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.config-legend {
  margin: 0 0 1rem;
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

.color-hex-input {
  max-width: 10rem;
  margin-top: 0.35rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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

<style>
/* Shared event-config section utilities (used by section subcomponents). */
.event-config .catalog-loading-hint,
.event-config-stations-section .catalog-loading-hint {
  margin: 0 0 0.75rem;
}

.event-config .muted,
.event-config-stations-section .muted,
.event-config-kitchen-monitors-section .muted {
  opacity: 0.65;
}

.event-config .section-toolbar,
.event-config-stations-section .section-toolbar,
.event-config-kitchen-monitors-section .section-toolbar,
.event-config-waiters-section .section-toolbar,
.event-config-cash-registers-section .section-toolbar,
.event-config-vouchers-section .section-toolbar,
.event-config-layouts-section .section-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.event-config .config-card,
.event-config-stations-section .config-card,
.event-config-kitchen-monitors-section .config-card,
.event-config-cash-registers-section .config-card,
.event-config-vouchers-section .config-card,
.event-config-layouts-section .config-card {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  background: rgba(var(--v-theme-on-surface), 0.02);
}

.event-config .config-card-header,
.event-config-stations-section .config-card-header,
.event-config-kitchen-monitors-section .config-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.event-config .error,
.event-config-stations-section .error {
  margin-bottom: 0.75rem;
}

.event-config label,
.event-config-stations-section label,
.event-config-kitchen-monitors-section label {
  font-size: 0.875rem;
  font-weight: 600;
}

@media (max-width: 992px) {
  .event-config-stations-section .config-card-header,
  .event-config-kitchen-monitors-section .config-card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
