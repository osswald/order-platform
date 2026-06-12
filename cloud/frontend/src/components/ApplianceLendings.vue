<template>
  <ListDetailLayout
    :title="$t('lending.pageTitle')"
    :subtitle="$t('lending.pageSubtitle')"
    :showCreate="false"
    :showDetail="false"
  >
    <template #header-actions>
      <HelpLink slug="appliance-lending" variant="icon" />
    </template>
    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        {{ $t('common.noOrganisation') }}
      </p>

      <template v-else>
        <p v-if="message" :class="messageType">{{ message }}</p>

        <p v-else-if="!lendings" class="muted-hint">{{ $t('common.loading') }}</p>

        <div v-else class="lend-sections">
          <div class="lend-section">
            <h3>{{ $t('lending.currentTitle') }}</h3>
            <VqDataTable
              :headers="lendingHeaders"
              :items="lendings.current"
              item-value="lending_id"
              hide-default-footer
              :no-data-text="$t('lending.noCurrent')"
              class="vq-data-table list-table lending-table"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || $t('common.emDash') }}</template>
              <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
              <template #item.period="{ item }">
                {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
              </template>
            </VqDataTable>
          </div>

          <div class="lend-section">
            <h3>{{ $t('lending.plannedTitle') }}</h3>
            <VqDataTable
              :headers="plannedLendingHeaders"
              :items="lendings.planned"
              item-value="lending_id"
              hide-default-footer
              :no-data-text="$t('lending.noPlanned')"
              class="vq-data-table list-table lending-table lending-table--planned"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || $t('common.emDash') }}</template>
              <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
              <template #item.period="{ item }">
                {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  variant="outlined"
                  type="button"
                  :disabled="cancellingLendingId === item.lending_id"
                  @click="cancelPlannedLendingRow(item)"
                >
                  {{ $t('common.cancelLending') }}
                </v-btn>
              </template>
            </VqDataTable>
          </div>

          <div class="lend-section">
            <h3>{{ $t('lending.pastTitle') }}</h3>
            <VqDataTable
              :headers="lendingHeaders"
              :items="lendings.past"
              item-value="lending_id"
              hide-default-footer
              :no-data-text="$t('lending.noPast')"
              class="vq-data-table list-table lending-table"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || $t('common.emDash') }}</template>
              <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
              <template #item.period="{ item }">
                {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
              </template>
            </VqDataTable>
          </div>
        </div>
      </template>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import { apiFetch } from '../api'
import {
  cancelPlannedLending,
  applianceTypeLabel,
  formatDeDate,
} from '../utils/applianceLending'
import VqDataTable from './VqDataTable.vue'

const { t } = useI18n()

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const COL_ID = { width: '5rem', sortable: false }
const COL_NAME = { minWidth: '12rem', sortable: false }
const COL_TYPE = { width: '8rem', sortable: false }
const COL_PERIOD = { width: '14rem', sortable: false }
const COL_ACTIONS = { align: 'end', width: '9rem', sortable: false }

const lendingHeaders = computed(() => [
  { title: t('common.id'), key: 'appliance_id', ...COL_ID },
  { title: t('common.appliance'), key: 'appliance_name', ...COL_NAME, sortable: false },
  { title: t('common.type'), key: 'appliance_type', ...COL_TYPE },
  { title: t('common.period'), key: 'period', ...COL_PERIOD },
])

const plannedLendingHeaders = computed(() => [
  ...lendingHeaders.value,
  { title: t('common.action'), key: 'actions', ...COL_ACTIONS },
])

const lendings = ref(null)
const message = ref('')
const messageType = ref('')
const cancellingLendingId = ref(null)

async function fetchLendings() {
  message.value = ''
  lendings.value = null
  if (props.activeOrganisationId == null) return

  try {
    const response = await apiFetch(
      `/organisations/${props.activeOrganisationId}/appliance-lendings`,
    )
    if (!response.ok) {
      message.value = t('lending.loadError')
      messageType.value = 'error'
      return
    }
    lendings.value = await response.json()
  } catch {
    message.value = t('lending.loadError')
    messageType.value = 'error'
  }
}

async function cancelPlannedLendingRow(row) {
  if (props.activeOrganisationId == null || !row?.lending_id) return
  const label = row.appliance_name || t('lending.deviceFallback', { id: row.appliance_id })
  if (!confirm(t('lending.cancelConfirm', { label }))) return
  cancellingLendingId.value = row.lending_id
  message.value = ''
  try {
    await cancelPlannedLending(props.activeOrganisationId, row.lending_id)
    message.value = t('lending.cancelSuccess')
    messageType.value = 'success'
    await fetchLendings()
  } catch (e) {
    message.value = e.message || t('lending.cancelFailed')
    messageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

watch(
  () => props.activeOrganisationId,
  () => {
    fetchLendings()
  },
)

onMounted(() => {
  fetchLendings()
})
</script>

<style scoped>
.empty-hint,
.muted-hint {
  opacity: 0.7;
  margin: 0 0 1rem;
}

.lend-sections {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.lend-section h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

@media (min-width: 993px) {
  .lend-sections :deep(.lending-table table) {
    table-layout: fixed;
    width: 100%;
  }

  .lend-sections :deep(.lending-table th),
  .lend-sections :deep(.lending-table td) {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .lend-sections :deep(.lending-table th:nth-child(1)),
  .lend-sections :deep(.lending-table td:nth-child(1)) {
    width: 5rem;
  }

  .lend-sections :deep(.lending-table th:nth-child(2)),
  .lend-sections :deep(.lending-table td:nth-child(2)) {
    width: auto;
  }

  .lend-sections :deep(.lending-table th:nth-child(3)),
  .lend-sections :deep(.lending-table td:nth-child(3)) {
    width: 8rem;
  }

  .lend-sections :deep(.lending-table th:nth-child(4)),
  .lend-sections :deep(.lending-table td:nth-child(4)) {
    width: 14rem;
  }

  .lend-sections :deep(.lending-table--planned th:nth-child(5)),
  .lend-sections :deep(.lending-table--planned td:nth-child(5)) {
    width: 9rem;
  }
}

@media (max-width: 992px) {
  .lend-sections {
    gap: 1rem;
  }
}
</style>
