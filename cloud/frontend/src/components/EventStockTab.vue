<template>
  <div class="event-stock-tab">
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <p v-if="message" :class="messageType">{{ message }}</p>
      <p v-if="!itemsLocal.length" class="muted">
        Keine Artikel an Stationen dieses Events verknüpft. Artikel zuerst unter „Stationen“ zuweisen.
      </p>
      <template v-else>
        <section v-for="group in stockGroups" :key="group.key" class="stock-group">
          <h3>{{ group.name }}</h3>
          <DataTable
            :value="group.items"
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
        </section>
      </template>
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
import { ref, watch, computed } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import { apiFetch } from '../api'
import { stockGroupsForItems } from '../utils/stockByStation'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
  stations: {
    type: Array,
    default: () => [],
  },
})

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref('')
const itemsLocal = ref([])

const stockGroups = computed(() => stockGroupsForItems(itemsLocal.value, props.stations))

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
.stock-group {
  margin-bottom: 1.5rem;
}
.stock-group h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}
</style>
