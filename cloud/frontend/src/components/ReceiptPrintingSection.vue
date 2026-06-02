<template>
  <div class="receipt-printing-section">
    <h3>{{ title }}</h3>
    <p v-if="hint" class="muted hint">{{ hint }}</p>
    <p v-if="!entityId" class="muted">Zuerst speichern, dann Beleg-Einstellungen bearbeiten.</p>
    <p v-else-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else>
      <div class="form-field logo-field">
        <label>Logo (Station, Kunde &amp; Zahlungsbeleg)</label>
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
          <v-btn
            type="button"
            variant="outlined"
            :disabled="logoBusy"
            @click="fileInput?.click()"
          >
            Logo hochladen
          </v-btn>
          <v-btn
            v-if="hasReceiptLogo || logoPreviewUrl"
            type="button"
            color="error"
            variant="outlined"
            :disabled="logoBusy"
            @click="removeLogo"
          >
            Logo entfernen
          </v-btn>
        </div>
        <small>PNG oder JPEG, max. 200 KB. Upload wird sofort gespeichert.</small>
      </div>

      <div v-if="isEvent" class="form-field">
        <label>Event-Titel (Label)</label>
        <v-text-field
          v-model="config.label_event_title"
          placeholder="Leer = Veranstaltungsname"
          density="compact"
          hide-details
        />
        <small>Nur für diese Veranstaltung. Wird gedruckt, wenn «Event-Titel anzeigen» aktiv ist.</small>
      </div>

      <v-tabs v-model="receiptTab" density="comfortable" class="receipt-tabs">
        <v-tab value="station">Station / Küche</v-tab>
        <v-tab value="customer">Kunde (Abholbeleg)</v-tab>
        <v-tab value="payment">Belege</v-tab>
      </v-tabs>
      <v-window v-model="receiptTab" class="receipt-tab-panels">
        <v-window-item value="station">
          <ReceiptProfileFields
            v-model="config.station_receipt"
            pickup-label="Tisch / Pickup"
            :show-price-option="false"
          />
        </v-window-item>
        <v-window-item value="customer">
          <ReceiptProfileFields v-model="config.customer_receipt" pickup-label="Pickup-Code" />
        </v-window-item>
        <v-window-item value="payment">
          <PaymentReceiptProfileFields v-model="config.payment_receipt" />
        </v-window-item>
      </v-window>

      <div class="actions">
        <v-btn
          color="primary"
          type="button"
          :disabled="saving"
          @click="save"
        >
          Beleg-Einstellungen speichern
        </v-btn>
      </div>
      <p v-if="saveMessage" class="muted">{{ saveMessage }}</p>
    </template>
  </div>
</template>

<script setup>
import { ref, toRef, watch } from 'vue'
import PaymentReceiptProfileFields from './PaymentReceiptProfileFields.vue'
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
const receiptTab = ref('station')
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
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.hint {
  margin-bottom: 0.75rem;
}

.logo-preview {
  display: flex;
  justify-content: center;
  padding: 0.75rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
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

.receipt-tabs {
  margin-top: 0.5rem;
}

.receipt-tab-panels {
  padding-top: 0.5rem;
}
</style>
