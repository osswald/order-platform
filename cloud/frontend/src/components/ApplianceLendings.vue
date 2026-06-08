<template>
  <ListDetailLayout
    title="Geräteausleihen"
    subtitle="Ausleihen für die aktive Organisation (nur Lesen)."
    :showCreate="false"
    :showDetail="false"
  >
    <template #header-actions>
      <HelpLink slug="appliance-lending" variant="icon" />
    </template>
    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>

      <template v-else>
        <p v-if="message" :class="messageType">{{ message }}</p>

        <p v-else-if="!lendings" class="muted-hint">Laden…</p>

        <div v-else class="lend-sections">
          <div class="lend-section">
            <h3>Aktuell ausgeliehene Geräte</h3>
            <VqDataTable
              :headers="lendingHeaders"
              :items="lendings.current"
              item-value="lending_id"
              hide-default-footer
              no-data-text="Keine aktiven Ausleihen."
              class="vq-data-table list-table lending-table"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || '—' }}</template>
              <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
              <template #item.period="{ item }">
                {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
              </template>
            </VqDataTable>
          </div>

          <div class="lend-section">
            <h3>Geplante Ausleihen</h3>
            <VqDataTable
              :headers="plannedLendingHeaders"
              :items="lendings.planned"
              item-value="lending_id"
              hide-default-footer
              no-data-text="Keine geplanten Ausleihen."
              class="vq-data-table list-table lending-table lending-table--planned"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || '—' }}</template>
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
                  Stornieren
                </v-btn>
              </template>
            </VqDataTable>
          </div>

          <div class="lend-section">
            <h3>Vergangene Ausleihen</h3>
            <VqDataTable
              :headers="lendingHeaders"
              :items="lendings.past"
              item-value="lending_id"
              hide-default-footer
              no-data-text="Keine vergangenen Ausleihen."
              class="vq-data-table list-table lending-table"
            >
              <template #item.appliance_name="{ item }">{{ item.appliance_name || '—' }}</template>
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
import { ref, watch, onMounted } from 'vue'
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import { apiFetch } from '../api'
import { cancelPlannedLending } from '../utils/applianceLending'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const COL_ID = { width: '5rem' }
const COL_NAME = { minWidth: '12rem' }
const COL_TYPE = { width: '8rem', sortable: false }
const COL_PERIOD = { width: '14rem', sortable: false }
const COL_ACTIONS = { align: 'end', width: '9rem', sortable: false }

const lendingHeaders = [
  { title: 'ID', key: 'appliance_id', ...COL_ID },
  { title: 'Gerät', key: 'appliance_name', ...COL_NAME, sortable: false },
  { title: 'Typ', key: 'appliance_type', ...COL_TYPE },
  { title: 'Zeitraum', key: 'period', ...COL_PERIOD },
]

const plannedLendingHeaders = [
  ...lendingHeaders,
  { title: 'Aktion', key: 'actions', ...COL_ACTIONS },
]

const lendings = ref(null)
const message = ref('')
const messageType = ref('')
const cancellingLendingId = ref(null)

const APPLIANCE_TYPE_LABELS = {
  server: 'Server',
  printer: 'Drucker',
  mobile: 'Mobil',
  tablet: 'Tablet',
  router: 'Router',
  ap: 'Access Point',
}

function applianceTypeLabel(type) {
  return APPLIANCE_TYPE_LABELS[type] || type
}

function formatDeDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = String(iso).split('T')[0].split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('de-DE')
}

async function fetchLendings() {
  message.value = ''
  lendings.value = null
  if (props.activeOrganisationId == null) return

  try {
    const response = await apiFetch(
      `/organisations/${props.activeOrganisationId}/appliance-lendings`,
    )
    if (!response.ok) {
      message.value = 'Ausleihen konnten nicht geladen werden.'
      messageType.value = 'error'
      return
    }
    lendings.value = await response.json()
  } catch {
    message.value = 'Ausleihen konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

async function cancelPlannedLendingRow(row) {
  if (props.activeOrganisationId == null || !row?.lending_id) return
  const label = row.appliance_name || `Gerät #${row.appliance_id}`
  if (!confirm(`Geplante Ausleihe für „${label}“ wirklich stornieren?`)) return
  cancellingLendingId.value = row.lending_id
  message.value = ''
  try {
    await cancelPlannedLending(props.activeOrganisationId, row.lending_id)
    message.value = 'Geplante Ausleihe storniert.'
    messageType.value = 'success'
    await fetchLendings()
  } catch (e) {
    message.value = e.message || 'Stornierung fehlgeschlagen.'
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

@media (max-width: 1000px) {
  .lend-sections {
    gap: 1.25rem;
  }
}

@media (max-width: 700px) {
  .lend-sections {
    gap: 1rem;
  }
}
</style>
