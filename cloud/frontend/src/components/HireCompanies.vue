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
      <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>

      <v-form ref="formRef" @submit.prevent="saveCompany">
      <div class="form-field">
        <FormLabel required>Name</FormLabel>
        <v-text-field
          v-model="form.name"
          placeholder="Vendiqo"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <label>Adresse</label>
        <v-text-field v-model="form.address" placeholder="Musterstraße 12" hide-details="auto" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>PLZ</label>
          <v-text-field v-model="form.zip" placeholder="8000" hide-details="auto" />
        </div>
        <div class="form-field">
          <label>Stadt</label>
          <v-text-field v-model="form.city" placeholder="Zürich" hide-details="auto" />
        </div>
      </div>
      <div class="form-field">
        <label>Land</label>
        <v-text-field v-model="form.country" placeholder="Schweiz" hide-details="auto" />
      </div>
      <ReceiptPrintingSection
        v-if="editMode && routeEntityId"
        :api-base-path="`/hire-companies/${routeEntityId}`"
        :entity-id="routeEntityId"
        title="Beleg-Vorlagen (Verleiher)"
        hint="Standard für neue Organisationen. Wird bei Organisationserstellung übernommen."
      />
      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" type="submit">Speichern</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Verleiher</h2>
        <span>{{ companies.length }} Einträge</span>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="companies"
        item-value="id"
        hover
        hide-default-footer
        no-data-text="Keine Verleiher gefunden."
        class="vq-data-table list-table"
        @click:row="(_e, { item }) => editCompany(item)"
      >
        <template #item.standort="{ item }">
          {{ item.address || '—' }}<span v-if="item.city"> · {{ item.city }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="text" @click.stop="deleteCompany(item.id)">Löschen</v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { inject, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import FormLabel from './FormLabel.vue'
import ListDetailLayout from './ListDetailLayout.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import { apiFetch } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

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

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'Standort', key: 'standort', sortable: false },
  { title: 'Land', key: 'country' },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

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

const formRef = ref(null)

async function saveCompany() {
  if (!(await validateForm(formRef))) return
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
  color: rgb(var(--v-theme-on-surface));
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}
</style>
