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
          <p v-if="catalogLoading" class="muted catalog-loading-hint">{{ $t('events.config.catalogLoading') }}</p>
          <p v-else-if="catalogError" class="error">{{ catalogError }}</p>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addStation">{{ $t('events.config.addStation') }}</v-btn>
          </div>
          <div v-for="(st, idx) in stationsLocal" :key="'st-' + idx" class="config-card">
            <div class="config-card-header">
              <span>{{ st.name || $t('events.config.unnamedStation') }}</span>
              <v-btn
                icon="mdi-delete"
                variant="text"
                color="error"
                type="button"
                :aria-label="$t('events.config.remove')"
                @click="removeStation(idx)"
              />
            </div>
            <div class="form-field">
              <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
              <v-text-field
                v-model="st.name"
                :placeholder="$t('events.config.stationNamePlaceholder')"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </div>
            <div class="form-field">
              <label>{{ $t('events.config.printer') }}</label>
              <v-select
                v-model="st.printer_appliance_id"
                :items="printerOptions"
                item-title="name"
                item-value="id"
                :placeholder="$t('events.config.noPrinter')"
                clearable
                density="compact"
                hide-details
              />
            </div>
            <div v-if="alternativePrintersEnabled" class="printer-rules-block">
              <div class="printer-rules-header">
                <label>{{ $t('events.config.printerRules') }}</label>
                <v-btn size="small" variant="text" type="button" @click="addPrinterRule(idx)">
                  {{ $t('events.config.addRule') }}
                </v-btn>
              </div>
              <div
                v-for="(rule, ruleIdx) in st.printer_rules"
                :key="'rule-' + idx + '-' + ruleIdx"
                class="printer-rule-card"
              >
                <div class="printer-rule-card-header">
                  <span>{{ $t('events.config.ruleN', { n: ruleIdx + 1 }) }}</span>
                  <v-btn
                    icon="mdi-delete"
                    variant="text"
                    color="error"
                    type="button"
                    :aria-label="$t('events.config.removeRule')"
                    @click="removePrinterRule(idx, ruleIdx)"
                  />
                </div>
                <div class="form-field">
                  <label>{{ $t('events.config.ruleType') }}</label>
                  <v-select
                    v-model="rule.rule_type"
                    :items="printerRuleTypeOptions"
                    item-title="label"
                    item-value="value"
                    density="compact"
                    hide-details
                  />
                </div>
                <template v-if="rule.rule_type === 'table_range'">
                  <div class="rule-range-row">
                    <div class="form-field">
                      <label>{{ $t('events.config.tableFrom') }}</label>
                      <v-text-field
                        v-model.number="rule.table_from"
                        type="number"
                        min="1"
                        max="99999"
                        density="compact"
                        hide-details
                      />
                    </div>
                    <div class="form-field">
                      <label>{{ $t('events.config.tableTo') }}</label>
                      <v-text-field
                        v-model.number="rule.table_to"
                        type="number"
                        min="1"
                        max="99999"
                        density="compact"
                        hide-details
                      />
                    </div>
                  </div>
                </template>
                <div v-else-if="rule.rule_type === 'pickup_prefix'" class="form-field">
                  <label>{{ $t('events.config.pickupPrefix') }}</label>
                  <v-text-field
                    v-model="rule.pickup_prefix"
                    :placeholder="$t('events.config.pickupPrefixPlaceholder')"
                    maxlength="3"
                    density="compact"
                    hide-details
                    @update:model-value="rule.pickup_prefix = normalizePickupPrefix($event)"
                  />
                </div>
                <div class="form-field">
                  <label>{{ $t('events.config.printer') }}</label>
                  <v-select
                    v-model="rule.printer_appliance_id"
                    :items="printerOptions"
                    item-title="name"
                    item-value="id"
                    :placeholder="$t('events.config.noPrinter')"
                    clearable
                    density="compact"
                    hide-details
                  />
                </div>
              </div>
            </div>
            <div class="form-field">
              <label>{{ $t('events.config.articles') }}</label>
              <v-select
                v-model="st.article_ids"
                :items="articleOptions"
                item-title="name"
                item-value="value"
                :placeholder="$t('events.config.selectArticles')"
                :loading="catalogLoading"
                :disabled="catalogLoading"
                multiple
                chips
                closable-chips
                density="compact"
                hide-details
              />
            </div>
          </div>
          <p v-if="!stationsLocal.length" class="muted">{{ $t('events.config.noStations') }}</p>
        </template>

        <template v-if="kitchenMonitorsEnabled" #kitchen-monitors>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addKitchenMonitorPrinter">{{ $t('events.config.addPrinter') }}</v-btn>
          </div>
          <div
            v-for="(row, idx) in kitchenMonitorsLocal"
            :key="'km-' + idx"
            class="config-card"
          >
            <div class="config-card-header">
              <span>{{ kitchenMonitorLabel(row) }}</span>
              <v-btn
                icon="mdi-delete"
                variant="text"
                color="error"
                type="button"
                :aria-label="$t('events.config.remove')"
                @click="removeKitchenMonitorPrinter(idx)"
              />
            </div>
            <div class="form-field">
              <label>{{ $t('events.config.printer') }}</label>
              <v-select
                v-model="row.printer_appliance_id"
                :items="kitchenMonitorPrinterOptions"
                item-title="name"
                item-value="id"
                :placeholder="$t('events.config.selectPrinter')"
                density="compact"
                hide-details
              />
            </div>
            <div class="form-field">
              <label>{{ $t('events.config.displayNameOptional') }}</label>
              <v-text-field
                v-model="row.label"
                :placeholder="$t('events.config.displayNamePlaceholder')"
                density="compact"
                hide-details
              />
            </div>
          </div>
          <p v-if="!kitchenMonitorsLocal.length" class="muted">{{ $t('events.config.noKitchenMonitors') }}</p>
        </template>

        <template #kellner>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addWaiterRow">{{ $t('events.config.addWaiter') }}</v-btn>
            <v-btn variant="outlined" type="button" :disabled="catalogLoading" @click="openWaiterPick">{{ $t('events.config.importFromOrg') }}</v-btn>
          </div>
          <VqDataTable
            :items="waitersLocal"
            item-value="_key"
            :headers="waiterHeaders"
            class="vq-data-table nested"
            hide-default-footer
          >
            <template #item.name="{ index }">
              <v-text-field
                v-model="waitersLocal[index].name"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </template>
            <template #item.pin="{ index }">
              <v-text-field
                v-model="waitersLocal[index].pin"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </template>
            <template v-if="accountsEnabled" #item.subsidiary_code="{ index }">
              <v-text-field
                v-model="waitersLocal[index].subsidiary_code"
                density="compact"
                hide-details="auto"
                maxlength="32"
              />
            </template>
            <template #item.actions="{ index }">
              <v-btn
                icon="mdi-delete"
                variant="text"
                color="error"
                type="button"
                @click="removeWaiterByIndex(index)"
              />
            </template>
          </VqDataTable>
        </template>

        <template v-if="cashRegistersEnabled" #kassen>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addCashRegister">{{ $t('events.config.addCashRegister') }}</v-btn>
          </div>
          <div v-for="(reg, ri) in cashRegistersLocal" :key="'reg-' + ri" class="config-card">
            <div class="config-card-header">
              <span>{{ reg.name || $t('events.config.unnamedCashRegister') }}</span>
              <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeCashRegister(ri)" />
            </div>
            <div class="field-row">
              <div class="form-field">
                <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
                <v-text-field
                  v-model="reg.name"
                  :placeholder="$t('events.config.cashRegisterPlaceholder')"
                  density="compact"
                  hide-details="auto"
                  required
                  :rules="[rules.required]"
                />
              </div>
              <div class="form-field">
                <label>{{ $t('events.config.pickupCodeLetters') }}</label>
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
                <label>{{ $t('events.config.pin') }}</label>
                <v-text-field v-model="reg.pin" maxlength="4" placeholder="0000" density="compact" hide-details />
              </div>
              <div v-if="accountsEnabled" class="form-field">
                <label>{{ $t('events.config.subsidiaryCode') }}</label>
                <v-text-field
                  v-model="reg.subsidiary_code"
                  maxlength="32"
                  density="compact"
                  hide-details
                />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>{{ $t('events.config.layout') }}</label>
                <v-select
                  v-model="reg.layout_uuid"
                  :items="layoutOptions"
                  item-title="name"
                  item-value="value"
                  :placeholder="$t('events.config.selectLayout')"
                  density="compact"
                  hide-details
                />
              </div>
              <div class="form-field">
                <label>{{ $t('events.config.customerPrinter') }}</label>
                <v-select
                  v-model="reg.receipt_printer_appliance_id"
                  :items="printerOptions"
                  item-title="name"
                  item-value="id"
                  :placeholder="$t('events.config.noPrinter')"
                  clearable
                  density="compact"
                  hide-details
                />
              </div>
            </div>
          </div>
          <p v-if="!cashRegistersLocal.length" class="muted">{{ $t('events.config.noCashRegisters') }}</p>
        </template>

        <template v-if="vouchersEnabled" #gutscheine>
          <div class="section-toolbar">
            <v-btn color="primary" type="button" @click="addVoucher">{{ $t('events.config.addVoucher') }}</v-btn>
          </div>
          <p v-if="!vouchersLocal.length" class="muted">{{ $t('events.config.noVouchers') }}</p>
          <div v-for="(vd, vi) in vouchersLocal" :key="'vd-' + vi" class="config-card">
            <div class="config-card-header">
              <span>{{ vd.name || $t('events.config.unnamedVoucher') }}</span>
              <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeVoucher(vi)" />
            </div>
            <div class="form-field">
              <FormLabel required>{{ $t('events.config.name') }}</FormLabel>
              <v-text-field
                v-model="vd.name"
                :placeholder="$t('events.config.voucherPlaceholder')"
                density="compact"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </div>
            <div class="form-field">
              <label>{{ $t('events.config.kind') }}</label>
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
              <label>{{ $t('events.config.amountWithCurrency', { currency: currencyLabel }) }}</label>
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
                <label>{{ $t('events.config.eligibleArticles') }}</label>
                <v-select
                  v-model="vd.allowed_article_ids"
                  :items="articleOptions"
                  item-title="name"
                  item-value="value"
                  :placeholder="$t('events.config.selectArticles')"
                  :loading="catalogLoading"
                  :disabled="catalogLoading"
                  multiple
                  chips
                  closable-chips
                  density="compact"
                  hide-details
                />
              </div>
              <v-checkbox
                v-model="vd.include_additions"
                :label="$t('events.config.includeAdditions')"
                hide-details
                density="compact"
              />
            </template>
          </div>
        </template>

        <template #layouts>
          <p v-if="layoutCellsLoading" class="muted catalog-loading-hint">{{ $t('events.config.layoutCellsLoading') }}</p>
          <p v-else-if="layoutCellsError" class="error">{{ layoutCellsError }}</p>
          <div v-if="!layoutCellsLoading && layoutCellsLoaded" class="section-toolbar">
            <v-btn color="primary" type="button" @click="addLayout">{{ $t('events.config.addLayout') }}</v-btn>
          </div>
          <div v-for="(lo, li) in layoutsLocal" v-show="!layoutCellsLoading && layoutCellsLoaded" :key="'lo-' + li" class="config-card">
            <div class="config-card-header">
              <span>{{ $t('events.config.layoutN', { n: li + 1 }) }}</span>
              <div class="layout-header-actions">
                <v-checkbox
                  :model-value="lo.is_default"
                  :label="$t('events.config.default')"
                  hide-details
                  density="compact"
                  @update:model-value="(v) => onDefaultLayoutChange(li, v)"
                />
                <v-btn icon="mdi-delete" variant="text" color="error" type="button" @click="removeLayout(li)" />
              </div>
            </div>
            <div class="field-row">
              <div class="form-field">
                <label>{{ $t('events.config.name') }}</label>
                <v-text-field v-model="lo.name" :placeholder="$t('events.config.optional')" density="compact" hide-details />
              </div>
              <div class="form-field">
                <label>{{ $t('events.config.width') }}</label>
                <v-number-input
                  :model-value="lo.grid_width"
                  :min="1"
                  :max="64"
                  control-variant="stacked"
                  density="compact"
                  hide-details
                  @update:model-value="(v) => onGridWidthChange(lo, v)"
                />
              </div>
              <div class="form-field">
                <label>{{ $t('events.config.height') }}</label>
                <v-number-input
                  :model-value="lo.grid_height"
                  :min="1"
                  :max="64"
                  control-variant="stacked"
                  density="compact"
                  hide-details
                  @update:model-value="(v) => onGridHeightChange(lo, v)"
                />
              </div>
            </div>
            <p class="muted small">{{ $t('events.config.clickCellsToEdit') }}</p>
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
                  :style="previewCellStyle(displayCell(lo, pos.row, pos.col))"
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

    <v-dialog v-model="cellDialogVisible" max-width="32rem" class="cell-dialog">
      <v-card>
        <v-card-title>{{ $t('events.config.editCell') }}</v-card-title>
        <v-card-text>
          <div class="form-field">
            <label>{{ $t('events.config.label') }}</label>
            <v-text-field v-model="cellEdit.label" density="compact" hide-details />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.color') }}</label>
            <v-color-picker v-model="cellEdit.color" mode="hex" hide-inputs />
            <v-text-field
              v-model="cellEdit.color"
              density="compact"
              hide-details
              placeholder="#eeeeee"
              class="color-hex-input"
            />
          </div>
          <div v-if="vouchersEnabled" class="form-field">
            <label>{{ $t('events.config.fixedAmountVouchers') }}</label>
            <v-select
              v-model="cellEdit.voucher_definition_uuids"
              :items="fixedAmountVoucherOptions"
              item-title="label"
              item-value="value"
              :placeholder="$t('events.config.selectVouchers')"
              multiple
              chips
              closable-chips
              density="compact"
              hide-details
            />
          </div>
          <div class="form-field">
            <label>{{ $t('events.config.stationArticlesOnly') }}</label>
            <v-text-field
              v-model="cellTreeFilter"
              :placeholder="$t('events.config.filterArticles')"
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
          <v-btn variant="outlined" type="button" @click="cellDialogVisible = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" type="button" @click="applyCellDialog">{{ $t('events.config.apply') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showWaiterPick" max-width="32rem">
      <v-card>
        <v-card-title>{{ $t('events.config.importWaiter') }}</v-card-title>
        <v-card-text>
          <p v-if="catalogLoading" class="muted">{{ $t('events.config.catalogLoading') }}</p>
          <p v-else-if="catalogError" class="error">{{ catalogError }}</p>
          <div class="form-field">
            <label>{{ $t('events.config.waiter') }}</label>
            <v-select
              v-model="pickedWaiterIds"
              :items="waiterOptions"
              item-title="label"
              item-value="value"
              :placeholder="$t('events.config.selectWaiters')"
              :loading="catalogLoading"
              :disabled="catalogLoading"
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
          <v-btn variant="outlined" type="button" @click="closeWaiterPick">{{ $t('common.cancel') }}</v-btn>
          <v-btn
            color="primary"
            type="button"
            :disabled="!pickedWaiterIds.length"
            @click="confirmPickWaiter"
          >
            {{ $t('events.config.apply') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, useSlots, onMounted, onBeforeUnmount, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../api'
import { parseApiErrorDetail } from '../utils/apiError'
import { useBreakpoint } from '../composables/useBreakpoint'
import { MOBILE_BREAKPOINT } from '../constants/layout'
import { useDirtyAutosave } from '../composables/useDirtyAutosave'
import { loadOrgCatalog } from '../composables/useOrgCatalog'
import SectionNavLayout from './SectionNavLayout.vue'
import EventSaveStatusBar from './EventSaveStatusBar.vue'
import EventStockTab from './EventStockTab.vue'
import EventSalesTab from './EventSalesTab.vue'
import EventCollectiveBillsTab from './EventCollectiveBillsTab.vue'
import EventTransactionsTab from './EventTransactionsTab.vue'
import EventCashSessionsTab from './EventCashSessionsTab.vue'
import EventBookkeepingTab from './EventBookkeepingTab.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import FormLabel from './FormLabel.vue'
import { rules } from '../utils/formRules.js'
import { textColorForBackground } from '../utils/colorContrast.js'
import { organisationAccountsEnabled } from '../utils/orgScope.js'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
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

const waiterHeaders = computed(() => {
  const headers = [
    { title: t('events.config.waiterNameHeader'), key: 'name', sortable: false },
    { title: t('events.config.waiterPinHeader'), key: 'pin', sortable: false },
  ]
  if (accountsEnabled.value) {
    headers.push({ title: t('events.config.subsidiaryCode'), key: 'subsidiary_code', sortable: false })
  }
  headers.push({ title: '', key: 'actions', sortable: false, align: 'end', width: '4rem' })
  return headers
})

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
const layoutCellsLoaded = ref(false)
const layoutCellsLoading = ref(false)
const layoutCellsError = ref('')

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

function kitchenMonitorLabel(row) {
  if ((row.label || '').trim()) return row.label.trim()
  const match = printerOptions.value.find((opt) => Number(opt.id) === Number(row.printer_appliance_id))
  return match?.name || t('events.config.printerFallback', { id: row.printer_appliance_id || '?' })
}

function addPrinterRule(stationIdx) {
  const st = stationsLocal.value[stationIdx]
  if (!st) return
  if (!Array.isArray(st.printer_rules)) st.printer_rules = []
  st.printer_rules.push({
    rule_type: 'table_range',
    table_from: 1,
    table_to: 50,
    pickup_prefix: 'A',
    printer_appliance_id: null,
  })
}

function removePrinterRule(stationIdx, ruleIdx) {
  const st = stationsLocal.value[stationIdx]
  if (!st?.printer_rules) return
  st.printer_rules.splice(ruleIdx, 1)
}

function addKitchenMonitorPrinter() {
  kitchenMonitorsLocal.value.push({
    printer_appliance_id: kitchenMonitorPrinterOptions.value[0]?.id ?? null,
    label: '',
  })
}

function removeKitchenMonitorPrinter(idx) {
  kitchenMonitorsLocal.value.splice(idx, 1)
}

const waiterOptions = computed(() =>
  waitersOrg.value.map((w) => ({ label: w.name, value: w.id })),
)

const layoutOptions = computed(() =>
  layoutsLocal.value.map((lo, idx) => ({
    name: lo.name?.trim() || t('events.config.layoutN', { n: idx + 1 }),
    value: lo.uuid,
  })),
)

const fixedAmountVoucherOptions = computed(() =>
  vouchersLocal.value
    .filter((vd) => vd.kind === 'fixed_amount' && vd.uuid)
    .map((vd) => ({
      label: vd.name || t('events.config.voucherFallback'),
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

function previewCellStyle(cell) {
  const background = cell.color || '#eeeeee'
  return {
    background,
    color: textColorForBackground(background),
  }
}

function cellVoucherUuids(c) {
  const list = c?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) return list.map(String)
  if (c?.voucher_definition_uuid) return [String(c.voucher_definition_uuid)]
  return []
}

function clampGridDim(value, fallback = 4) {
  const n = Math.round(Number(value))
  if (!Number.isFinite(n)) return fallback
  return Math.min(64, Math.max(1, n))
}

function isCellInGrid(c, width, height) {
  return c.row >= 0 && c.col >= 0 && c.row < height && c.col < width
}

function cellHasData(c) {
  if ((c.label || '').trim()) return true
  if ((c.article_ids || []).length > 0) return true
  if (cellVoucherUuids(c).length > 0) return true
  const color = (c.color || '').toLowerCase()
  if (color && color !== '#eeeeee' && color !== '#eee') return true
  return false
}

function applyGridSizeChange(lo, nextW, nextH) {
  const prevW = lo.grid_width
  const prevH = lo.grid_height
  nextW = clampGridDim(nextW, prevW)
  nextH = clampGridDim(nextH, prevH)
  if (nextW === prevW && nextH === prevH) return true

  if (nextW >= prevW && nextH >= prevH) {
    lo.grid_width = nextW
    lo.grid_height = nextH
    return true
  }

  if (!Array.isArray(lo.cells)) lo.cells = []

  lo.cells = lo.cells.filter((c) => {
    if (isCellInGrid(c, nextW, nextH)) return true
    return !cellHasData(c)
  })

  const oobWithData = lo.cells.filter((c) => !isCellInGrid(c, nextW, nextH) && cellHasData(c))
  if (oobWithData.length) {
    const examples = oobWithData
      .slice(0, 3)
      .map((c) => t('events.config.gridRowCol', { row: c.row + 1, col: c.col + 1 }))
      .join('; ')
    const more = oobWithData.length > 3 ? t('events.config.gridConfirmMore') : ''
    const msg =
      oobWithData.length === 1
        ? t('events.config.gridConfirmSingle', { examples })
        : t('events.config.gridConfirmMultiple', { count: oobWithData.length, examples, more })
    if (!confirm(msg)) return false
    lo.cells = lo.cells.filter((c) => isCellInGrid(c, nextW, nextH))
  }

  lo.grid_width = nextW
  lo.grid_height = nextH
  return true
}

function onGridWidthChange(lo, value) {
  applyGridSizeChange(lo, value, lo.grid_height)
}

function onGridHeightChange(lo, value) {
  applyGridSizeChange(lo, lo.grid_width, value)
}

function cellPreviewMeta(lo, row, col) {
  const c = displayCell(lo, row, col)
  const vCount = cellVoucherUuids(c).length
  const aCount = c.article_ids?.length || 0
  const parts = []
  if (vCount) parts.push(t('events.config.voucherCount', vCount, { count: vCount }))
  if (aCount) parts.push(t('events.config.articleCount', { count: aCount }))
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
      name: t('events.config.defaultLayoutName'),
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
    name: t('events.config.stationFallback', { n: stationsLocal.value.length + 1 }),
    printer_appliance_id: null,
    printer_rules: [],
    article_ids: [],
  })
}

function removeStation(idx) {
  stationsLocal.value.splice(idx, 1)
}

function addWaiterRow() {
  waiterKey += 1
  waitersLocal.value.push({ _key: `nw-${waiterKey}`, name: '', pin: '0000', source_waiter_id: null, subsidiary_code: '' })
}

function removeWaiterByIndex(ix) {
  if (ix >= 0) waitersLocal.value.splice(ix, 1)
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

function addLayout() {
  layoutsLocal.value.push({
    uuid: newUuid(),
    name: t('events.config.layoutN', { n: layoutsLocal.value.length + 1 }),
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
    name: t('events.config.cashRegisterFallback', { n: cashRegistersLocal.value.length + 1 }),
    pickup_code_prefix: String.fromCharCode(65 + (cashRegistersLocal.value.length % 26)),
    pin: '0000',
    layout_uuid: layoutsLocal.value[0]?.uuid || '',
    receipt_printer_appliance_id: null,
    subsidiary_code: '',
  })
}

function removeCashRegister(idx) {
  cashRegistersLocal.value.splice(idx, 1)
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
  ensureDefaultLayout()
  layoutCellsLoaded.value = includeLayoutCells
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

function mergeLayoutCellsFromResponse(cfg) {
  const remoteByUuid = new Map((cfg.app_layouts || []).map((lo) => [lo.uuid, lo]))
  layoutsLocal.value = layoutsLocal.value.map((lo) => {
    const remote = remoteByUuid.get(lo.uuid)
    if (!remote) return lo
    return {
      ...lo,
      cells: mapLayoutCells(remote.cells),
    }
  })
  layoutCellsLoaded.value = true
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

async function loadLayoutCells() {
  if (layoutCellsLoaded.value || layoutCellsLoading.value) return
  layoutCellsLoading.value = true
  layoutCellsError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/configuration`)
    if (!resp.ok) throw new Error(await resp.text())
    mergeLayoutCellsFromResponse(await resp.json())
  } catch {
    layoutCellsError.value = t('events.config.layoutCellsLoadFailed')
  } finally {
    layoutCellsLoading.value = false
  }
}

async function loadConfiguration() {
  loading.value = true
  loadError.value = ''
  catalogError.value = ''
  layoutCellsError.value = ''
  layoutCellsLoaded.value = false
  articlesRaw.value = []
  waitersOrg.value = []
  if (resetConfigSnapshot) resetConfigSnapshot()
  try {
    const cfgRes = await apiFetch(`/events/${props.eventId}/configuration?fields=summary`)
    if (!cfgRes.ok) throw new Error(await cfgRes.text())
    applyConfigurationFromResponse(await cfgRes.json(), { includeLayoutCells: false })
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

async function openCellDialog(layoutIndex, row, col) {
  cellEditLayoutIndex.value = layoutIndex
  cellEditRow.value = row
  cellEditCol.value = col
  cellTreeFilter.value = ''
  const lo = layoutsLocal.value[layoutIndex]
  const c = displayCell(lo, row, col)
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
    const response = await apiFetch(`/events/${props.eventId}/configuration`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPutPayload()),
    })
    if (!response.ok) {
      setConfigAutosaveError(await parseApiErrorDetail(response))
      return false
    }
    const cfg = await response.json()
    printerOptions.value = cfg.printer_options || []
    return true
  } catch {
    setConfigAutosaveError(t('events.config.saveFailed'))
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
  () => !loading.value && !loadError.value && !cellDialogVisible.value,
)

const {
  status: configAutosaveStatus,
  errorMessage: configAutosaveError,
  markSaved: markConfigSaved,
  resetSnapshot: resetConfigSnapshot,
  flush: flushConfigAutosave,
  setError: setConfigAutosaveError,
  isDirty: configIsDirty,
} = useDirtyAutosave({
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
  if (tab === 'layouts') void loadLayoutCells()
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

.printer-rules-block {
  margin-bottom: 0.75rem;
}

.printer-rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.printer-rule-card {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  background: rgb(var(--v-theme-surface));
}

.printer-rule-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
}

.rule-range-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
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
  .field-row,
  .rule-range-row {
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
