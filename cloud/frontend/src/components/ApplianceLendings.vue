<template>
  <ListDetailLayout
    title="Geräteausleihen"
    subtitle="Ausleihen für die aktive Organisation (nur Lesen)."
    :showCreate="false"
    :showDetail="false"
  >
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
              class="vq-data-table list-table"
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
              class="vq-data-table list-table"
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
              class="vq-data-table list-table"
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
import { apiFetch } from '../api'
import { cancelPlannedLending } from '../utils/applianceLending'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const lendingHeaders = [
  { title: 'ID', key: 'appliance_id' },
  { title: 'Gerät', key: 'appliance_name', sortable: false },
  { title: 'Typ', key: 'appliance_type', sortable: false },
  { title: 'Zeitraum', key: 'period', sortable: false },
]

const plannedLendingHeaders = [
  ...lendingHeaders,
  { title: 'Aktion', key: 'actions', sortable: false, align: 'end' },
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
