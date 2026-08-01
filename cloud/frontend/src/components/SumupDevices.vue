<template>
  <ListDetailLayout
    :title="$t('sumupDevices.title')"
    :subtitle="$t('sumupDevices.subtitle')"
    :showCreate="false"
    :showDetail="false"
  >
    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        {{ $t('common.noOrganisation') }}
      </p>

      <template v-else>
        <p v-if="pageMessage" :class="pageMessageType">{{ pageMessage }}</p>

        <p v-if="loadingStatus" class="muted-hint">{{ $t('sumupDevices.loadingStatus') }}</p>
        <p v-else-if="loadError" class="error-text">{{ loadError }}</p>

        <template v-else-if="status">
          <p v-if="!status.configured" class="error-text">{{ status.error }}</p>

          <template v-else-if="!status.connected">
            <p class="muted">{{ $t('sumupDevices.connectDescription') }}</p>
            <v-btn
              color="primary"
              type="button"
              :loading="busy && busyAction === 'connect'"
              :disabled="busy"
              @click="startConnect"
            >
              {{ $t('sumupDevices.connect') }}
            </v-btn>
          </template>

          <template v-else>
            <div class="status-block">
              <v-chip color="success" variant="tonal" size="small">
                {{ $t('sumupDevices.connected') }}
              </v-chip>
              <p v-if="status.merchant_code" class="muted small mono">
                {{ $t('sumupDevices.merchantCode') }}: {{ status.merchant_code }}
              </p>
              <p class="muted small">
                {{ $t('sumupDevices.readerCount', { count: status.reader_count }) }}
              </p>
              <v-btn
                variant="outlined"
                color="error"
                type="button"
                :loading="busy && busyAction === 'disconnect'"
                :disabled="busy"
                @click="disconnect"
              >
                {{ $t('sumupDevices.disconnect') }}
              </v-btn>
            </div>

            <div class="readers-block">
              <h3>{{ $t('sumupDevices.readersTitle') }}</h3>
              <p v-if="loadingReaders" class="muted-hint">{{ $t('sumupDevices.loadingReaders') }}</p>
              <p v-else-if="readersError" class="error-text">{{ readersError }}</p>
              <template v-else>
                <VqDataTable
                  :headers="readerHeaders"
                  :items="readers"
                  item-value="id"
                  hide-default-footer
                  :no-data-text="$t('sumupDevices.noReaders')"
                  class="vq-data-table list-table readers-table"
                >
                  <template #item.status="{ item }">
                    {{ formatReaderStatus(item.status) }}
                  </template>
                  <template #item.actions="{ item }">
                    <div class="reader-actions">
                      <v-btn variant="outlined" type="button" @click="openRenameDialog(item)">
                        {{ $t('sumupDevices.rename') }}
                      </v-btn>
                      <v-btn
                        color="error"
                        variant="outlined"
                        type="button"
                        :loading="busy && busyAction === `unpair-${item.id}`"
                        :disabled="busy"
                        @click="unpairReader(item)"
                      >
                        {{ $t('sumupDevices.unpair') }}
                      </v-btn>
                    </div>
                  </template>
                </VqDataTable>

                <div class="pair-form">
                  <h4>{{ $t('sumupDevices.pairTitle') }}</h4>
                  <p class="muted small">{{ $t('sumupDevices.pairHint') }}</p>
                  <p class="form-required-legend">
                    <span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}
                  </p>
                  <v-form ref="pairFormRef" @submit.prevent="submitPair">
                    <div class="form-row">
                      <div class="form-field">
                        <FormLabel required>{{ $t('sumupDevices.pairingCode') }}</FormLabel>
                        <v-text-field
                          v-model="pairForm.pairing_code"
                          :placeholder="$t('sumupDevices.pairingCodePlaceholder')"
                          hide-details="auto"
                          :rules="[rules.required]"
                        />
                      </div>
                      <div class="form-field">
                        <FormLabel required>{{ $t('sumupDevices.readerLabel') }}</FormLabel>
                        <v-text-field
                          v-model="pairForm.label"
                          :placeholder="$t('sumupDevices.readerLabelPlaceholder')"
                          hide-details="auto"
                          :rules="[rules.required]"
                        />
                      </div>
                    </div>
                    <v-btn
                      color="primary"
                      type="submit"
                      :loading="busy && busyAction === 'pair'"
                      :disabled="busy"
                    >
                      {{ $t('sumupDevices.pair') }}
                    </v-btn>
                  </v-form>
                </div>
              </template>
            </div>
          </template>
        </template>
      </template>
    </template>
  </ListDetailLayout>

  <v-dialog v-model="renameDialogOpen" max-width="28rem">
    <v-card>
      <v-card-title>{{ $t('sumupDevices.renameTitle') }}</v-card-title>
      <v-card-text>
        <v-form ref="renameFormRef" @submit.prevent="submitRename">
          <FormLabel required>{{ $t('sumupDevices.readerLabel') }}</FormLabel>
          <v-text-field
            v-model="renameLabel"
            :placeholder="$t('sumupDevices.readerLabelPlaceholder')"
            hide-details="auto"
            :rules="[rules.required]"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn variant="outlined" type="button" @click="renameDialogOpen = false">
          {{ $t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          type="button"
          :loading="busy && busyAction === 'rename'"
          :disabled="busy"
          @click="submitRename"
        >
          {{ $t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import FormLabel from './FormLabel.vue'
import VqDataTable from './VqDataTable.vue'
import {
  authorizeSumupOrganisation,
  disconnectSumupOrganisation,
  fetchSumupOrganisationStatus,
  fetchSumupReaders,
  pairSumupReader,
  renameSumupReader,
  unpairSumupReader,
  type SumupOrganisationStatusView,
  type SumupReader,
} from '../utils/sumupCloud'
import { rules, validateForm, type ValidatableForm } from '../utils/formRules'
import { getErrorMessage } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const props = withDefaults(
  defineProps<{
    activeOrganisationId?: number | null
  }>(),
  {
    activeOrganisationId: null,
  },
)

const status = ref<SumupOrganisationStatusView | null>(null)
const readers = ref<SumupReader[]>([])
const loadingStatus = ref(false)
const loadingReaders = ref(false)
const loadError = ref('')
const readersError = ref('')
const busy = ref(false)
const busyAction = ref('')
const pageMessage = ref('')
const pageMessageType = ref('')

const pairForm = ref({ pairing_code: '', label: '' })
const pairFormRef = ref<ValidatableForm | null>(null)

const renameDialogOpen = ref(false)
const renameReaderId = ref<number | null>(null)
const renameLabel = ref('')
const renameFormRef = ref<ValidatableForm | null>(null)

const readerHeaders = computed((): DataTableHeader[] => [
  { title: t('sumupDevices.readerLabel'), key: 'label', sortable: false },
  { title: t('sumupDevices.status'), key: 'status', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

function formatReaderStatus(value: string): string {
  const key = `sumupDevices.readerStatus.${value}`
  const translated = t(key)
  return translated === key ? value : translated
}

function clearPageMessage() {
  pageMessage.value = ''
  pageMessageType.value = ''
}

function setPageMessage(message: string, type: string) {
  pageMessage.value = message
  pageMessageType.value = type
}

async function loadStatus() {
  const orgId = props.activeOrganisationId
  if (orgId == null) {
    status.value = null
    readers.value = []
    return
  }
  loadingStatus.value = true
  loadError.value = ''
  clearPageMessage()
  try {
    status.value = await fetchSumupOrganisationStatus(orgId)
  } catch (e: unknown) {
    status.value = null
    loadError.value = getErrorMessage(e, t('sumupDevices.statusLoadFailed'))
  } finally {
    loadingStatus.value = false
  }
}

async function loadReaders() {
  const orgId = props.activeOrganisationId
  if (orgId == null || !status.value?.configured || !status.value.connected) {
    readers.value = []
    return
  }
  loadingReaders.value = true
  readersError.value = ''
  try {
    readers.value = await fetchSumupReaders(orgId)
  } catch (e: unknown) {
    readers.value = []
    readersError.value = getErrorMessage(e, t('sumupDevices.readersLoadFailed'))
  } finally {
    loadingReaders.value = false
  }
}

async function reloadAll() {
  await loadStatus()
  await loadReaders()
}

async function startConnect() {
  const orgId = props.activeOrganisationId
  if (orgId == null) return
  busy.value = true
  busyAction.value = 'connect'
  clearPageMessage()
  try {
    const result = await authorizeSumupOrganisation(orgId)
    if (result.authorize_url) {
      // replace() avoids back-button return to a half-finished connect click
      window.location.replace(result.authorize_url)
      return
    }
    setPageMessage(t('sumupDevices.noAuthorizeUrl'), 'error-text')
  } catch (e: unknown) {
    setPageMessage(getErrorMessage(e, t('sumupDevices.connectFailed')), 'error-text')
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

async function disconnect() {
  const orgId = props.activeOrganisationId
  if (orgId == null) return
  busy.value = true
  busyAction.value = 'disconnect'
  clearPageMessage()
  try {
    await disconnectSumupOrganisation(orgId)
    setPageMessage(t('sumupDevices.disconnected'), 'success-text')
    await reloadAll()
  } catch (e: unknown) {
    setPageMessage(getErrorMessage(e, t('sumupDevices.disconnectFailed')), 'error-text')
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

async function submitPair() {
  const orgId = props.activeOrganisationId
  if (orgId == null) return
  if (!(await validateForm(pairFormRef))) return
  busy.value = true
  busyAction.value = 'pair'
  clearPageMessage()
  try {
    await pairSumupReader(orgId, {
      pairing_code: pairForm.value.pairing_code.trim(),
      label: pairForm.value.label.trim(),
    })
    pairForm.value = { pairing_code: '', label: '' }
    setPageMessage(t('sumupDevices.paired'), 'success-text')
    await reloadAll()
  } catch (e: unknown) {
    setPageMessage(getErrorMessage(e, t('sumupDevices.pairFailed')), 'error-text')
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

function openRenameDialog(reader: SumupReader) {
  renameReaderId.value = reader.id
  renameLabel.value = reader.label
  renameDialogOpen.value = true
}

async function submitRename() {
  const orgId = props.activeOrganisationId
  const readerId = renameReaderId.value
  if (orgId == null || readerId == null) return
  if (!(await validateForm(renameFormRef))) return
  busy.value = true
  busyAction.value = 'rename'
  clearPageMessage()
  try {
    await renameSumupReader(orgId, readerId, renameLabel.value.trim())
    renameDialogOpen.value = false
    setPageMessage(t('sumupDevices.renamed'), 'success-text')
    await loadReaders()
    await loadStatus()
  } catch (e: unknown) {
    setPageMessage(getErrorMessage(e, t('sumupDevices.renameFailed')), 'error-text')
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

async function unpairReader(reader: SumupReader) {
  const orgId = props.activeOrganisationId
  if (orgId == null) return
  if (!confirm(t('sumupDevices.unpairConfirm', { label: reader.label }))) return
  busy.value = true
  busyAction.value = `unpair-${reader.id}`
  clearPageMessage()
  try {
    await unpairSumupReader(orgId, reader.id)
    setPageMessage(t('sumupDevices.unpaired'), 'success-text')
    await reloadAll()
  } catch (e: unknown) {
    setPageMessage(getErrorMessage(e, t('sumupDevices.unpairFailed')), 'error-text')
  } finally {
    busy.value = false
    busyAction.value = ''
  }
}

function handleOAuthReturnQuery() {
  if (route.query.connected === '1') {
    setPageMessage(t('sumupDevices.connectedSuccess'), 'success-text')
    void router.replace({ name: 'sumup-devices', query: {} })
    void reloadAll()
    return
  }
  const oauthError = route.query.error
  if (typeof oauthError === 'string' && oauthError.trim()) {
    setPageMessage(oauthError, 'error-text')
    void router.replace({ name: 'sumup-devices', query: {} })
  }
}

watch(
  () => props.activeOrganisationId,
  async () => {
    await reloadAll()
  },
  { immediate: true },
)

watch(
  () => route.query,
  () => {
    handleOAuthReturnQuery()
  },
  { immediate: true },
)
</script>

<style scoped>
.empty-hint,
.muted-hint {
  opacity: 0.7;
  margin: 0 0 1rem;
}

.muted {
  opacity: 0.85;
}

.small {
  font-size: 0.9rem;
}

.mono {
  font-family: ui-monospace, monospace;
}

.status-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.readers-block h3,
.pair-form h4 {
  margin: 0 0 1rem;
}

.pair-form {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.reader-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.25rem;
}

.success-text {
  color: var(--vq-success, #22c55e);
}

.error-text {
  color: var(--vq-error, #ef4444);
}
</style>
