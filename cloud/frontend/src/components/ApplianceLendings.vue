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
            <DataTable
              :value="lendings.current"
              dataKey="lending_id"
              class="list-table"
              responsiveLayout="scroll"
            >
              <template #empty>Keine aktiven Ausleihen.</template>
              <Column field="appliance_id" header="ID" />
              <Column header="Gerät">
                <template #body="{ data }">{{ data.appliance_name || '—' }}</template>
              </Column>
              <Column header="Typ">
                <template #body="{ data }">{{ applianceTypeLabel(data.appliance_type) }}</template>
              </Column>
              <Column header="Zeitraum">
                <template #body="{ data }">{{ formatDeDate(data.start_date) }} – {{ formatDeDate(data.end_date) }}</template>
              </Column>
            </DataTable>
          </div>

          <div class="lend-section">
            <h3>Geplante Ausleihen</h3>
            <DataTable
              :value="lendings.planned"
              dataKey="lending_id"
              class="list-table"
              responsiveLayout="scroll"
            >
              <template #empty>Keine geplanten Ausleihen.</template>
              <Column field="appliance_id" header="ID" />
              <Column header="Gerät">
                <template #body="{ data }">{{ data.appliance_name || '—' }}</template>
              </Column>
              <Column header="Typ">
                <template #body="{ data }">{{ applianceTypeLabel(data.appliance_type) }}</template>
              </Column>
              <Column header="Zeitraum">
                <template #body="{ data }">{{ formatDeDate(data.start_date) }} – {{ formatDeDate(data.end_date) }}</template>
              </Column>
              <Column header="Aktion">
                <template #body="{ data }">
                  <Button
                    label="Stornieren"
                    class="secondary-button"
                    type="button"
                    :disabled="cancellingLendingId === data.lending_id"
                    @click="cancelPlannedLendingRow(data)"
                  />
                </template>
              </Column>
            </DataTable>
          </div>

          <div class="lend-section">
            <h3>Vergangene Ausleihen</h3>
            <DataTable
              :value="lendings.past"
              dataKey="lending_id"
              class="list-table"
              responsiveLayout="scroll"
            >
              <template #empty>Keine vergangenen Ausleihen.</template>
              <Column field="appliance_id" header="ID" />
              <Column header="Gerät">
                <template #body="{ data }">{{ data.appliance_name || '—' }}</template>
              </Column>
              <Column header="Typ">
                <template #body="{ data }">{{ applianceTypeLabel(data.appliance_type) }}</template>
              </Column>
              <Column header="Zeitraum">
                <template #body="{ data }">{{ formatDeDate(data.start_date) }} – {{ formatDeDate(data.end_date) }}</template>
              </Column>
            </DataTable>
          </div>
        </div>
      </template>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { cancelPlannedLending } from '../applianceLending'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

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
  color: var(--p-text-muted-color);
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
  color: var(--p-text-color);
}

.list-table {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  overflow: hidden;
}

.success,
.error {
  margin: 0 0 1rem;
}
</style>
