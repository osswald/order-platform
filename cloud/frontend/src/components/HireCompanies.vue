<template>
  <ListDetailLayout
    title="Verleiher"
    subtitle="Verleiher (Mandanten) verwalten — nur Plattform-Administratoren."
    createLabel="Neuer Verleiher"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Verleiher bearbeiten' : 'Neuer Verleiher' }}</h2>
      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Vendiqo" />
      </div>
      <div class="form-field">
        <label>Adresse</label>
        <InputText v-model="form.address" placeholder="Musterstraße 12" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>PLZ</label>
          <InputText v-model="form.zip" placeholder="8000" />
        </div>
        <div class="form-field">
          <label>Stadt</label>
          <InputText v-model="form.city" placeholder="Zürich" />
        </div>
      </div>
      <div class="form-field">
        <label>Land</label>
        <InputText v-model="form.country" placeholder="Schweiz" />
      </div>
      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button label="Speichern" class="primary-button" :disabled="!form.name" @click="saveCompany" />
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Verleiher</h2>
        <span>{{ companies.length }} Einträge</span>
      </div>
      <DataTable
        :value="companies"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editCompany($event.data)"
      >
        <template #empty>Keine Verleiher gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column header="Standort">
          <template #body="{ data }">
            {{ data.address || '—' }}<span v-if="data.city"> · {{ data.city }}</span>
          </template>
        </Column>
        <Column field="country" header="Land" />
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteCompany(data.id)" />
          </template>
        </Column>
      </DataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { inject, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { SESSION_CONTEXT_KEY } from '../sessionContext'

const sessionContext = inject(SESSION_CONTEXT_KEY, null)

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('hire-companies')

const companies = ref([])
const message = ref('')
const messageType = ref('')

const form = ref({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
})

async function fetchCompanies() {
  try {
    const resp = await apiFetch('/hire-companies/')
    if (!resp.ok) throw new Error(await resp.text())
    companies.value = await resp.json()
  } catch {
    message.value = 'Verleiher konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

const emptyForm = () => ({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
})

function applyCompanyToForm(row) {
  form.value = {
    name: row.name || '',
    address: row.address || '',
    zip: row.zip || '',
    city: row.city || '',
    country: row.country || '',
  }
  message.value = ''
}

function clearFormState() {
  form.value = emptyForm()
  message.value = ''
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearFormState()
    return
  }
  if (isCreateMode.value) {
    clearFormState()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = companies.value.find((c) => Number(c.id) === Number(id))
  if (!row) {
    try {
      const resp = await apiFetch(`/hire-companies/${id}`)
      if (!resp.ok) throw new Error(await resp.text())
      row = await resp.json()
    } catch {
      message.value = 'Verleiher nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyCompanyToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editCompany(row) {
  applyCompanyToForm(row)
  goToDetail(row.id)
}

async function saveCompany() {
  const payload = {
    name: form.value.name,
    address: form.value.address || null,
    zip: form.value.zip || null,
    city: form.value.city || null,
    country: form.value.country || null,
  }
  try {
    const path = editMode.value
      ? `/hire-companies/${routeEntityId.value}`
      : '/hire-companies/'
    const method = editMode.value ? 'PUT' : 'POST'
    const resp = await apiFetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok) throw new Error(await resp.text())
    const saved = await resp.json()
    const wasEdit = editMode.value
    await fetchCompanies()
    if (!wasEdit && sessionContext) {
      await sessionContext.reloadHireCompaniesAndSelect(saved.id)
    }
    message.value = wasEdit ? 'Verleiher aktualisiert.' : 'Verleiher erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = 'Fehler beim Speichern.'
    messageType.value = 'error'
  }
}

async function deleteCompany(id) {
  if (!confirm('Verleiher wirklich löschen? Nur möglich ohne Organisationen.')) return
  try {
    const resp = await apiFetch(`/hire-companies/${id}`, { method: 'DELETE' })
    if (!resp.ok) throw new Error(await resp.text())
    await fetchCompanies()
    message.value = 'Verleiher gelöscht.'
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Verleiher konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(fetchCompanies)
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: var(--p-text-color);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.85rem;
}

.success {
  color: var(--p-green-700);
  margin-top: 1rem;
}

.error {
  color: var(--p-red-700);
  margin-top: 1rem;
}

@media (max-width: 768px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
