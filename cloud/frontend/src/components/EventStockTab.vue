<template>
  <div class="event-stock-tab">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <p v-if="message" :class="messageType">{{ message }}</p>
      <p v-if="!itemsLocal.length" class="muted">
        Keine Artikel an Stationen dieses Events verknüpft. Artikel zuerst unter „Stationen“ zuweisen.
      </p>
      <DataTable
        v-else
        :value="itemsLocal"
        dataKey="id"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column field="name" header="Artikel" />
        <Column header="Bestand führen">
          <template #body="{ data }">
            <Checkbox v-model="data.monitor_stock" :binary="true" />
          </template>
        </Column>
        <Column header="Bestand">
          <template #body="{ data }">
            <InputNumber
              v-model="data.in_stock"
              :min="0"
              :disabled="!data.monitor_stock"
              class="stock-qty-input"
            />
          </template>
        </Column>
      </DataTable>
      <div class="section-toolbar" style="margin-top: 1rem">
        <Button
          label="Lager speichern"
          class="primary-button"
          type="button"
          :disabled="saving || loading"
          @click="saveStock"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import { apiFetch } from '../api'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
})

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('')
const itemsLocal = ref([])

async function loadStock() {
  if (!props.eventId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/event-stock`)
    if (!resp.ok) throw new Error(await resp.text())
    const data = await resp.json()
    itemsLocal.value = (data.items || []).map((row) => ({
      id: row.id,
      name: row.name,
      label: row.label,
      monitor_stock: !!row.monitor_stock,
      in_stock: row.monitor_stock ? (row.in_stock ?? 0) : 0,
    }))
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    itemsLocal.value = []
  } finally {
    loading.value = false
  }
}

async function saveStock() {
  if (!props.eventId) return
  saving.value = true
  message.value = ''
  try {
    const payload = {
      items: itemsLocal.value.map((row) => ({
        article_id: row.id,
        monitor_stock: !!row.monitor_stock,
        in_stock: row.monitor_stock ? (row.in_stock ?? 0) : null,
      })),
    }
    const resp = await apiFetch(`/events/${props.eventId}/event-stock`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok) throw new Error(await resp.text())
    const data = await resp.json()
    itemsLocal.value = (data.items || []).map((row) => ({
      id: row.id,
      name: row.name,
      label: row.label,
      monitor_stock: !!row.monitor_stock,
      in_stock: row.monitor_stock ? (row.in_stock ?? 0) : 0,
    }))
    message.value = 'Lager gespeichert.'
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || 'Speichern fehlgeschlagen'
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.eventId,
  () => {
    loadStock()
  },
  { immediate: true },
)
</script>

<style scoped>
.stock-qty-input {
  max-width: 8rem;
}
</style>
