<template>
  <ListDetailLayout
    :title="t('appliances.title')"
    :subtitle="t('appliances.subtitle')"
    :createLabel="t('appliances.createLabel')"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #header-actions>
      <HelpLink slug="appliance-pairing" variant="icon" />
    </template>
    <template #detail>
      <h2>{{ editMode ? t('appliances.editTitle') : t('appliances.createTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveAppliance">
      <div class="form-field">
        <v-select
          v-model="form.type"
          :items="typeOptions"
          item-title="label"
          item-value="value"
          :label="t('appliances.type')"
          :placeholder="t('appliances.typePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        >
          <template #item="{ item, props: itemProps }">
            <v-list-item v-bind="itemProps" :title="undefined">
              <ApplianceTypeChip :type="item.raw.value" />
            </v-list-item>
          </template>
          <template #selection="{ item }">
            <ApplianceTypeChip :type="item.raw.value" />
          </template>
        </v-select>
      </div>

      <div v-if="isAutoNamed" class="form-field">
        <v-text-field
          :model-value="form.name || t('appliances.autoNamePlaceholder')"
          :label="t('appliances.name')"
          disabled
          hide-details="auto"
        />
        <small>{{ autoNameHint }}</small>
      </div>

      <div v-else-if="form.type" class="form-field">
        <v-text-field v-model="form.name" :label="t('appliances.nameOptional')" :placeholder="t('appliances.displayNamePlaceholder')" hide-details="auto" />
      </div>

      <div v-if="isPrinter" class="form-field">
        <v-text-field v-model="form.ip_address" :label="t('appliances.ipAddress')" :placeholder="t('appliances.ipPlaceholder')" hide-details="auto" />
      </div>
      <div v-if="isPrinter" class="form-field">
        <v-text-field
          v-model.number="form.escpos_feed_lines"
          type="number"
          :min="0"
          :max="10"
          :label="t('appliances.escposFeedLines')"
          :hint="t('appliances.escposFeedHint')"
          persistent-hint
          hide-details="auto"
        />
      </div>

      <div class="form-field">
        <v-text-field v-model="form.model" :label="t('appliances.modelOptional')" :placeholder="t('appliances.modelPlaceholder')" hide-details="auto" />
      </div>

      <div class="form-field">
        <v-textarea v-model="form.comment" :label="t('appliances.commentOptional')" rows="3" :placeholder="t('appliances.commentPlaceholder')" hide-details="auto" />
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">{{ t('appliances.back') }}</v-btn>
        <v-btn color="primary" type="submit">{{ t('common.save') }}</v-btn>
      </div>
      </v-form>

      <template v-if="editMode && applianceDetail">
        <div v-if="applianceDetail.type === 'server'" class="lending-section edge-server-section">
          <h3>{{ t('appliances.edge.title') }}</h3>

          <div class="pairing-panel">
            <h4>{{ t('appliances.edge.sdCardsTitle') }}</h4>
            <p class="edge-credentials-hint">
              {{ t('appliances.edge.hint') }}
            </p>
            <v-btn color="primary" type="button" :disabled="pairingLoading" @click="createPairingSession">
              {{ t('appliances.edge.createPairingCode') }}
            </v-btn>
            <div v-if="pairingSession" class="pairing-code-card">
              <span class="pairing-code-label">{{ t('appliances.edge.pairingCodeLabel') }}</span>
              <strong>{{ pairingSession.pairing_code_display }}</strong>
              <p>
                {{ t('appliances.edge.pairingInstructionsBefore') }}
                <code>{{ pairingSession.setup_url }}</code>
                {{ t('appliances.edge.pairingInstructionsAfter', { expiresAt: formatDeDateTime(pairingSession.expires_at) }) }}
              </p>
            </div>
            <p v-if="pairingMessage" :class="pairingMessageType">{{ pairingMessage }}</p>

            <VqDataTable
              :headers="edgeCredentialsHeaders"
              :items="applianceDetail.edge_credentials || []"
              item-value="id"
              class="vq-data-table edge-installations-table"
              hide-default-footer
            >
              <template #item.label="{ item }">{{ item.label || t('appliances.edge.sdCardLabel', { id: item.id }) }}</template>
              <template #item.edge_client_id="{ item }">
                <span class="cell-truncate" :title="item.edge_client_id">{{ item.edge_client_id }}</span>
              </template>
              <template #item.status="{ item }">
                <v-chip
                  :color="item.status === 'active' ? 'success' : 'error'"
                  size="small"
                  variant="tonal"
                >
                  {{ item.status === 'active' ? t('appliances.edge.statusActive') : t('appliances.edge.statusBlocked') }}
                </v-chip>
              </template>
              <template #item.last_seen_at="{ item }">{{ formatDeDateTime(item.last_seen_at) }}</template>
              <template #item.actions="{ item }">
                <v-btn
                  v-if="item.status === 'active'"
                  variant="outlined"
                  size="small"
                  type="button"
                  @click="revokeEdgeCredential(item.id)"
                >
                  {{ t('appliances.edge.revoke') }}
                </v-btn>
                <v-btn
                  v-else
                  color="error"
                  variant="outlined"
                  size="small"
                  type="button"
                  @click="deleteEdgeCredential(item.id)"
                >
                  {{ t('common.delete') }}
                </v-btn>
              </template>
              <template #no-data>{{ t('appliances.edge.noSdCards') }}</template>
            </VqDataTable>
          </div>
        </div>

        <div class="lending-section">
          <h3>{{ t('appliances.lending.title') }}</h3>
          <p v-if="lendingStatusLent" class="lending-hint">
            {{ t('appliances.lending.lentHint') }}
          </p>
          <div class="lending-form">
            <div class="form-field">
              <v-select
                v-model="lendForm.organisationId"
                :items="organisationOptions"
                item-title="label"
                item-value="value"
                :label="t('appliances.lending.organisation')"
                :placeholder="t('appliances.lending.organisationPlaceholder')"
                :disabled="!organisationOptions.length"
                hide-details="auto"
              />
            </div>
            <div class="form-field">
              <v-date-input
                v-model="lendForm.startDate"
                :label="t('appliances.lending.startDate')"
                :placeholder="t('appliances.lending.startDate')"
                prepend-icon=""
                prepend-inner-icon="mdi-calendar"
                hide-details="auto"
                required
                :rules="[rules.requiredDate]"
              />
            </div>
            <div class="form-field">
              <v-date-input
                v-model="lendForm.endDate"
                :label="t('appliances.lending.endDate')"
                :placeholder="t('appliances.lending.endDate')"
                prepend-icon=""
                prepend-inner-icon="mdi-calendar"
                hide-details="auto"
                required
                :rules="[rules.requiredDate, lendEndDateRule]"
              />
            </div>
            <small v-if="lendRangeHint" class="lend-range-hint">{{ lendRangeHint }}</small>
            <v-btn color="primary" type="button" :disabled="!canSubmitLend" @click="submitLend">
              {{ t('appliances.lending.lend') }}
            </v-btn>
          </div>
          <p v-if="lendingMessage" :class="lendingMessageType">{{ lendingMessage }}</p>
        </div>

        <div class="lending-section">
          <h3>{{ t('appliances.lending.history') }}</h3>
          <VqDataTable
            :headers="lendingHistoryHeaders"
            :items="applianceDetail.lendings || []"
            item-value="id"
            class="vq-data-table lendings-table"
            hide-default-footer
          >
            <template #item.start_date="{ item }">{{ formatDeDate(item.start_date) }}</template>
            <template #item.end_date="{ item }">{{ formatDeDate(item.end_date) }}</template>
            <template #item.status="{ item }">{{ lendingHistoryStatusLabel(item) }}</template>
            <template #item.actions="{ item }">
              <v-btn
                v-if="item.segment === 'current' && !item.returned_at"
                variant="outlined"
                size="small"
                type="button"
                @click="returnLending(item.id)"
              >
                {{ t('appliances.lending.return') }}
              </v-btn>
              <v-btn
                v-else-if="item.segment === 'future'"
                variant="outlined"
                size="small"
                type="button"
                :disabled="cancellingLendingId === item.id"
                @click="cancelPlannedLendingRow(item.id)"
              >
                {{ t('appliances.lending.cancel') }}
              </v-btn>
              <span v-else>{{ t('common.emDash') }}</span>
            </template>
            <template #no-data>{{ t('appliances.lending.noLendings') }}</template>
          </VqDataTable>
        </div>
      </template>

      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <div class="table-header">
        <h2>{{ t('appliances.table.all') }}</h2>
        <span>{{ t('appliances.table.entryCount', { filtered: filteredAppliances.length, total: appliances.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="t('appliances.table.searchPlaceholder')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="typeFilter"
            :items="typeFilterOptions"
            item-title="label"
            item-value="value"
            :label="t('appliances.type')"
            hide-details
            density="compact"
          >
            <template #item="{ item, props: itemProps }">
              <v-list-item v-bind="itemProps" :title="undefined">
                <ApplianceTypeChip v-if="item.raw.value" :type="item.raw.value" />
                <span v-else>{{ item.raw.label }}</span>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              <ApplianceTypeChip v-if="item.raw.value" :type="item.raw.value" />
              <span v-else>{{ item.raw.label }}</span>
            </template>
          </v-select>
        </div>
        <div class="filter-field">
          <v-select
            v-model="ipFilter"
            :items="ipFilterOptions"
            item-title="label"
            item-value="value"
            :label="t('appliances.ipAddress')"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredAppliances"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="(_, { item }) => editAppliance(item)"
      >
        <template #item.name="{ item }">{{ applianceDisplayName(item) }}</template>
        <template #item.type="{ item }">
          <ApplianceTypeChip :type="item.type" />
        </template>
        <template #item.lending_status="{ item }">
          <v-chip
            :color="item.lending_status === 'lent' ? 'warning' : 'success'"
            size="small"
            variant="tonal"
          >
            {{ lendingStatusLabel(item.lending_status) }}
          </v-chip>
        </template>
        <template #item.organisation="{ item }">{{ item.current_lending?.organisation_name || t('common.emDash') }}</template>
        <template #item.end_date="{ item }">
          {{ item.current_lending?.end_date ? formatDeDate(item.current_lending.end_date) : t('common.emDash') }}
        </template>
        <template #item.ip_address="{ item }">
          {{ item.type === 'printer' ? item.ip_address || t('common.emDash') : t('common.emDash') }}
        </template>
        <template #item.model="{ item }">
          <span class="cell-truncate" :title="item.model || ''">{{ item.model || t('common.emDash') }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteAppliance(item.id)">
            {{ t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ t('appliances.table.noResults') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import ApplianceTypeChip from './ApplianceTypeChip.vue'
import { apiJson } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import {
  applianceDisplayName,
  cancelPlannedLendingForAppliance,
  defaultLendingEndDate,
  inclusiveDurationDays,
  isValidLendingRange,
  lendingRangeHint,
  toIsoDate,
} from '../utils/applianceLending'
import { APPLIANCE_TYPES, applianceTypeLabel } from '../utils/applianceType'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import VqDataTable from './VqDataTable.vue'

const { t } = useI18n()

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('appliances')

const appliances = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const typeFilter = ref('')
const ipFilter = ref('')

const tableHeaders = computed(() => [
  { title: t('appliances.table.id'), key: 'id' },
  { title: t('appliances.table.name'), key: 'name', sortable: false },
  { title: t('appliances.table.type'), key: 'type', sortable: false },
  { title: t('appliances.table.status'), key: 'lending_status', sortable: false },
  { title: t('appliances.table.organisation'), key: 'organisation', sortable: false },
  { title: t('appliances.table.until'), key: 'end_date', sortable: false },
  { title: t('appliances.table.ip'), key: 'ip_address', sortable: false },
  { title: t('appliances.table.model'), key: 'model', sortable: false },
  { title: t('appliances.table.actions'), key: 'actions', sortable: false, align: 'end' },
])

const edgeCredentialsHeaders = computed(() => [
  { title: t('appliances.table.sdCard'), key: 'label', sortable: false },
  { title: t('appliances.table.clientId'), key: 'edge_client_id', sortable: false },
  { title: t('appliances.table.status'), key: 'status', sortable: false },
  { title: t('appliances.table.lastSeen'), key: 'last_seen_at', sortable: false },
  { title: t('appliances.table.action'), key: 'actions', sortable: false, align: 'end' },
])

const lendingHistoryHeaders = computed(() => [
  { title: t('appliances.table.organisation'), key: 'organisation_name' },
  { title: t('appliances.table.from'), key: 'start_date', sortable: false },
  { title: t('appliances.table.to'), key: 'end_date', sortable: false },
  { title: t('appliances.table.status'), key: 'status', sortable: false },
  { title: t('appliances.table.action'), key: 'actions', sortable: false, align: 'end' },
])

const organisations = ref([])
const applianceDetail = ref(null)
const lendingMessage = ref('')
const lendingMessageType = ref('')
const pairingSession = ref(null)
const pairingMessage = ref('')
const pairingMessageType = ref('')
const pairingLoading = ref(false)
const cancellingLendingId = ref(null)
const lendForm = ref({
  organisationId: null,
  startDate: null,
  endDate: null,
})

const emptyForm = () => ({
  type: '',
  name: '',
  ip_address: '',
  escpos_feed_lines: 1,
  model: '',
  comment: '',
})

const form = ref(emptyForm())
const formRef = ref(null)

const isPrinter = computed(() => form.value.type === 'printer')
const isAutoNamed = computed(() => form.value.type === 'server' || form.value.type === 'printer')

const autoNameHint = computed(() => {
  if (form.value.type === 'server') {
    return t('appliances.autoNameHint.server')
  }
  if (form.value.type === 'printer') {
    return t('appliances.autoNameHint.printer')
  }
  return ''
})

const typeOptions = computed(() =>
  APPLIANCE_TYPES.map((value) => ({ value, label: t(`applianceType.${value}`) })),
)
const typeFilterOptions = computed(() => [
  { value: '', label: t('appliances.table.allTypes') },
  ...typeOptions.value,
])
const ipFilterOptions = computed(() => [
  { value: '', label: t('appliances.table.allIp') },
  { value: 'with-ip', label: t('appliances.table.withIp') },
  { value: 'without-ip', label: t('appliances.table.withoutIp') },
])

const organisationOptions = computed(() =>
  organisations.value.map((o) => ({ label: o.name, value: o.id })),
)

const lendingStatusLent = computed(() => applianceDetail.value?.lending_status === 'lent')

const lendEndDateRule = (value) =>
  isValidLendingRange(lendForm.value.startDate, value) ||
  t('appliances.lending.endDateAfterStart')

const lendRangeHint = computed(() =>
  lendingRangeHint(lendForm.value.startDate, lendForm.value.endDate),
)

const canSubmitLend = computed(() => {
  if (!lendForm.value.organisationId) return false
  return isValidLendingRange(lendForm.value.startDate, lendForm.value.endDate)
})

function matchesSearch(device, term) {
  if (!term) return true
  return [
    device.id,
    device.name,
    applianceTypeLabel(device.type),
    device.type,
    device.ip_address,
    device.model,
    device.comment,
    device.current_lending?.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

function lendingStatusLabel(status) {
  return status === 'lent' ? t('appliances.lending.statusLent') : t('appliances.lending.statusAvailable')
}

function lendingHistoryStatusLabel(row) {
  if (row.returned_at) return t('appliances.lending.historyReturned')
  if (row.segment === 'current') return t('appliances.lending.historyActive')
  if (row.segment === 'future') return t('appliances.lending.historyPlanned')
  return t('appliances.lending.historyExpired')
}

function formatDeDate(iso) {
  if (!iso) return t('common.emDash')
  const [y, m, d] = String(iso).split('T')[0].split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('de-DE')
}

function formatDeDateTime(iso) {
  if (!iso) return t('common.emDash')
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('de-DE')
}

const filteredAppliances = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return appliances.value.filter((device) => {
    if (!matchesSearch(device, term)) return false
    if (typeFilter.value && device.type !== typeFilter.value) return false
    const hasIp = !!device.ip_address
    if (ipFilter.value === 'with-ip' && !hasIp) return false
    if (ipFilter.value === 'without-ip' && hasIp) return false
    return true
  })
})

const { currentPage, pageSize } = useClientPagination(filteredAppliances, {
  resetOn: [searchQuery, typeFilter, ipFilter],
})

async function fetchAppliances() {
  try {
    appliances.value = await apiJson('/appliances/')
  } catch {
    message.value = t('appliances.messages.loadFailed')
    messageType.value = 'error'
  }
}

async function fetchOrganisations() {
  try {
    organisations.value = await apiJson('/organisations/')
  } catch {
    organisations.value = []
  }
}

async function fetchApplianceDetail(id) {
  lendingMessage.value = ''
  try {
    applianceDetail.value = await apiJson(`/appliances/${id}`)
  } catch {
    applianceDetail.value = null
    lendingMessage.value = t('appliances.lending.detailsLoadFailed')
    lendingMessageType.value = 'error'
  }
}

function resetLendForm() {
  const start = new Date()
  lendForm.value = {
    organisationId: null,
    startDate: start,
    endDate: defaultLendingEndDate(start),
  }
}

function clearDetailState() {
  form.value = emptyForm()
  message.value = ''
  applianceDetail.value = null
  pairingSession.value = null
  pairingMessage.value = ''
  resetLendForm()
  lendingMessage.value = ''
}

function applyDeviceToForm(device) {
  pairingSession.value = null
  pairingMessage.value = ''
  form.value = {
    type: device.type,
    name: device.name || '',
    ip_address: device.ip_address || '',
    escpos_feed_lines: device.escpos_feed_lines ?? 1,
    model: device.model || '',
    comment: device.comment || '',
  }
  message.value = ''
  resetLendForm()
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearDetailState()
    return
  }
  if (isCreateMode.value) {
    clearDetailState()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = appliances.value.find((d) => Number(d.id) === Number(id))
  if (!row) {
    try {
      row = await apiJson(`/appliances/${id}`)
    } catch {
      message.value = t('appliances.messages.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyDeviceToForm(row)
  await fetchApplianceDetail(id)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editAppliance(device) {
  applyDeviceToForm(device)
  goToDetail(device.id)
  fetchApplianceDetail(device.id)
}

function buildPayload() {
  const payload = {
    type: form.value.type,
    model: form.value.model?.trim() || null,
    comment: form.value.comment?.trim() || null,
  }
  if (form.value.type === 'printer') {
    payload.ip_address = form.value.ip_address?.trim() || null
    const feed = Number(form.value.escpos_feed_lines)
    payload.escpos_feed_lines = Number.isFinite(feed) ? Math.max(0, Math.min(10, Math.round(feed))) : 1
  }
  if (!isAutoNamed.value && form.value.name?.trim()) {
    payload.name = form.value.name.trim()
  }
  return payload
}

async function saveAppliance() {
  if (!(await validateForm(formRef))) return
  const payload = buildPayload()

  try {
    const path = editMode.value ? `/appliances/${activeId.value}` : '/appliances/'
    const method = editMode.value ? 'PUT' : 'POST'
    const wasEdit = editMode.value
    const body = await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const savedId = wasEdit ? activeId.value : body.id
    await fetchAppliances()
    if (wasEdit && savedId) {
      await fetchApplianceDetail(savedId)
      message.value = t('appliances.messages.updated')
      messageType.value = 'success'
    } else {
      message.value = t('appliances.messages.created')
      messageType.value = 'success'
      await goToList()
    }
  } catch {
    message.value = t('appliances.messages.saveFailed')
    messageType.value = 'error'
  }
}

async function createPairingSession() {
  if (!activeId.value || applianceDetail.value?.type !== 'server') return
  pairingLoading.value = true
  pairingMessage.value = ''
  pairingSession.value = null
  try {
    pairingSession.value = await apiJson(`/appliances/${activeId.value}/pairing-sessions`, { method: 'POST' })
    pairingMessage.value = t('appliances.edge.pairingCreated')
    pairingMessageType.value = 'success'
  } catch {
    pairingMessage.value = t('appliances.edge.pairingCreateFailed')
    pairingMessageType.value = 'error'
  } finally {
    pairingLoading.value = false
  }
}

async function revokeEdgeCredential(credentialId) {
  if (!activeId.value || !credentialId) return
  if (!confirm(t('appliances.edge.confirmRevoke'))) return
  try {
    applianceDetail.value = await apiJson(`/appliances/${activeId.value}/edge-credentials/${credentialId}/revoke`, {
      method: 'POST',
    })
    await fetchAppliances()
    message.value = t('appliances.edge.revoked')
    messageType.value = 'success'
  } catch {
    message.value = t('appliances.edge.revokeFailed')
    messageType.value = 'error'
  }
}

async function deleteEdgeCredential(credentialId) {
  if (!activeId.value || !credentialId) return
  if (!confirm(t('appliances.edge.confirmDelete'))) return
  try {
    await apiJson(`/appliances/${activeId.value}/edge-credentials/${credentialId}`, {
      method: 'DELETE',
    })
    await fetchApplianceDetail(activeId.value)
    await fetchAppliances()
    message.value = t('appliances.edge.deleted')
    messageType.value = 'success'
  } catch {
    message.value = t('appliances.edge.deleteFailed')
    messageType.value = 'error'
  }
}

async function deleteAppliance(id) {
  if (!confirm(t('appliances.messages.confirmDelete'))) {
    return
  }
  try {
    await apiJson(`/appliances/${id}`, {
      method: 'DELETE',
    })
    await fetchAppliances()
    message.value = t('appliances.messages.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('appliances.messages.deleteFailed')
    messageType.value = 'error'
  }
}

async function submitLend() {
  if (!activeId.value || !canSubmitLend.value) return
  lendingMessage.value = ''
  try {
    applianceDetail.value = await apiJson(`/appliances/${activeId.value}/lendings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        organisation_id: lendForm.value.organisationId,
        start_date: toIsoDate(lendForm.value.startDate),
        duration_days: inclusiveDurationDays(lendForm.value.startDate, lendForm.value.endDate),
      }),
    })
    await fetchAppliances()
    resetLendForm()
    lendingMessage.value = t('appliances.lending.lentCreated')
    lendingMessageType.value = 'success'
  } catch (e) {
    lendingMessage.value = e.message || t('appliances.lending.lendFailed')
    lendingMessageType.value = 'error'
  }
}

async function returnLending(lendingId) {
  if (!activeId.value) return
  lendingMessage.value = ''
  try {
    applianceDetail.value = await apiJson(
      `/appliances/${activeId.value}/lendings/${lendingId}/return`,
      { method: 'POST' },
    )
    await fetchAppliances()
    lendingMessage.value = t('appliances.lending.returned')
    lendingMessageType.value = 'success'
  } catch {
    lendingMessage.value = t('appliances.lending.returnFailed')
    lendingMessageType.value = 'error'
  }
}

async function cancelPlannedLendingRow(lendingId) {
  if (!activeId.value) return
  if (!confirm(t('appliances.lending.confirmCancel'))) return
  cancellingLendingId.value = lendingId
  lendingMessage.value = ''
  try {
    await cancelPlannedLendingForAppliance(activeId.value, lendingId)
    await fetchApplianceDetail(activeId.value)
    await fetchAppliances()
    lendingMessage.value = t('appliances.lending.cancelled')
    lendingMessageType.value = 'success'
  } catch (e) {
    lendingMessage.value = e.message || t('appliances.lending.cancelFailed')
    lendingMessageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

onMounted(() => {
  fetchAppliances()
  fetchOrganisations()
})
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

.optional,
small {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-weight: 400;
}

textarea {
  resize: vertical;
}

.input-readonly {
  opacity: 0.75;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.lending-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.edge-credentials-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  line-height: 1.4;
}

.edge-server-section {
  margin-top: 1.5rem;
}

.pairing-panel {
  margin-top: 1.25rem;
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.pairing-panel h4 {
  margin: 0 0 0.75rem;
}

.pairing-code-card {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.pairing-code-label {
  display: block;
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.pairing-code-card strong {
  display: block;
  font-family: ui-monospace, monospace;
  font-size: 1.75rem;
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
}

.pairing-code-card p {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.65);
  line-height: 1.4;
}

.lending-section h3 {
  margin: 0 0 1rem;
  font-size: 1.05rem;
  color: rgb(var(--v-theme-on-surface));
}

.lending-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 0.75rem;
}

.lend-range-hint {
  display: block;
  width: 100%;
  margin: 0 0 0.5rem;
  opacity: 0.75;
}

.lending-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lendings-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.table-header h2 {
  margin: 0;
}

.table-header span {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.9rem;
}

.list-controls {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 180px 180px;
  gap: 1rem;
  margin-bottom: 1rem;
}

.search-field,
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.list-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}

.cell-truncate {
  display: inline-block;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
}

.success,
.error {
  margin-top: 1rem;
}

@media (max-width: 1000px) {
  .list-controls {
    grid-template-columns: 1fr;
  }
}
</style>
