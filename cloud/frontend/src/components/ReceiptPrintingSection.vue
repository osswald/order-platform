<template>
  <div class="receipt-printing-section">
    <h3>{{ title }}</h3>
    <p v-if="hint" class="muted hint">{{ hint }}</p>
    <p v-if="!entityId" class="muted">Zuerst speichern, dann Beleg-Einstellungen bearbeiten.</p>
    <p v-else-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <div class="form-field logo-field">
        <label>Logo (Station &amp; Kunde)</label>
        <div v-if="logoPreviewUrl" class="logo-preview">
          <img :src="logoPreviewUrl" alt="Beleg-Logo" />
        </div>
        <input
          ref="fileInput"
          type="file"
          class="logo-file-input"
          accept="image/png,image/jpeg,.png,.jpg,.jpeg"
          @change="onLogoFile"
        />
        <div class="logo-actions">
          <Button
            type="button"
            label="Logo hochladen"
            class="secondary-button"
            :disabled="logoBusy"
            @click="fileInput?.click()"
          />
          <Button
            v-if="hasReceiptLogo || logoPreviewUrl"
            type="button"
            label="Logo entfernen"
            class="danger"
            :disabled="logoBusy"
            @click="removeLogo"
          />
        </div>
        <small>PNG oder JPEG, max. 200 KB. Upload wird sofort gespeichert.</small>
      </div>

      <div v-if="isEvent" class="form-field">
        <label>Event-Titel (Label)</label>
        <InputText
          v-model="config.label_event_title"
          placeholder="Leer = Veranstaltungsname"
        />
        <small>Nur für diese Veranstaltung. Wird gedruckt, wenn «Event-Titel anzeigen» aktiv ist.</small>
      </div>

      <TabView>
        <TabPanel header="Station / Küche">
          <ReceiptProfileFields v-model="config.station_receipt" pickup-label="Tisch / Pickup" />
        </TabPanel>
        <TabPanel header="Kunde (Abholbeleg)">
          <ReceiptProfileFields v-model="config.customer_receipt" pickup-label="Pickup-Code" />
        </TabPanel>
      </TabView>

      <div class="actions">
        <Button
          label="Beleg-Einstellungen speichern"
          class="primary-button"
          type="button"
          :disabled="saving"
          @click="save"
        />
      </div>
      <p v-if="saveMessage" class="muted">{{ saveMessage }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref, toRef, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import TabPanel from 'primevue/tabpanel'
import TabView from 'primevue/tabview'
import ReceiptProfileFields from './ReceiptProfileFields.vue'
import { useReceiptPrinting } from '../composables/useReceiptPrinting'

const props = defineProps({
  apiBasePath: { type: String, default: '' },
  entityId: { type: [Number, String], default: null },
  isEvent: { type: Boolean, default: false },
  title: { type: String, default: 'Belege' },
  hint: { type: String, default: '' },
})

const fileInput = ref(null)
const apiBasePathRef = toRef(props, 'apiBasePath')

const {
  loading,
  saving,
  logoBusy,
  loadError,
  saveMessage,
  hasReceiptLogo,
  logoPreviewUrl,
  config,
  load,
  save,
  uploadLogo,
  removeLogo,
} = useReceiptPrinting(apiBasePathRef, { isEvent: props.isEvent })

watch(
  () => [props.apiBasePath, props.entityId],
  ([path, id]) => {
    if (path && id) load()
  },
  { immediate: true },
)

function onLogoFile(event) {
  const file = event.target.files?.[0]
  if (file) uploadLogo(file)
  event.target.value = ''
}
</script>

<style scoped>
.receipt-printing-section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-surface-200);
}

.hint {
  margin-bottom: 0.75rem;
}

.logo-preview {
  display: flex;
  justify-content: center;
  padding: 0.75rem;
  background: var(--p-surface-100);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}

.logo-preview img {
  max-width: 220px;
  max-height: 120px;
  object-fit: contain;
}

.logo-file-input {
  display: none;
}

.logo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}
</style>
