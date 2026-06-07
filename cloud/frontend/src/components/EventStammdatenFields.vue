<template>
  <div class="event-stammdaten">
    <section class="field-group">
      <h3 class="field-group-title">Basis</h3>
      <div class="form-field">
        <FormLabel required>Name</FormLabel>
        <v-text-field
          v-model="form.name"
          placeholder="Sommerfest 2026"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="field-row">
        <div class="form-field">
          <FormLabel required>Status</FormLabel>
          <v-select
            v-model="form.status"
            :items="selectableStatusOptions"
            item-title="label"
            item-value="value"
            placeholder="Status wählen"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
        <div class="form-field">
          <FormLabel required>Währung</FormLabel>
          <v-select
            v-model="form.currency"
            :items="currencyOptions"
            placeholder="Währung wählen"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
      </div>
      <div class="field-row">
        <div class="form-field">
          <FormLabel required>Start</FormLabel>
          <v-text-field
            :model-value="formatLocalDatetime(form.start)"
            type="datetime-local"
            placeholder="Startdatum wählen"
            hide-details="auto"
            required
            :rules="[() => rules.requiredDate(props.form.start)]"
            @update:model-value="form.start = parseLocalDatetime($event)"
          />
        </div>
        <div class="form-field">
          <FormLabel required>Ende</FormLabel>
          <v-text-field
            :model-value="formatLocalDatetime(form.end)"
            type="datetime-local"
            placeholder="Enddatum wählen"
            hide-details="auto"
            required
            :rules="[() => rules.requiredDate(props.form.end)]"
            @update:model-value="form.end = parseLocalDatetime($event)"
          />
        </div>
      </div>
    </section>

    <section class="field-group">
      <h3 class="field-group-title">Zahlung</h3>
      <div class="form-field">
        <FormLabel>Zahlungsmodus (Pi / Kellner)</FormLabel>
        <v-select
          v-model="form.paymentMode"
          :items="paymentModeOptions"
          item-title="label"
          item-value="value"
          placeholder="Modus wählen"
          hide-details="auto"
        />
        <small>Sofort bezahlt = Position als bezahlt beim Absenden; Jetzt bezahlen = Bezahlen beim Abschicken der Bestellung; Später = Bezahlung erfolgt zu einem späteren Zeitpunkt.</small>
      </div>
      <div class="form-field">
        <FormLabel required>Zahlungsarten (Pi)</FormLabel>
        <v-select
          v-model="form.paymentTypes"
          :items="paymentTypeOptions"
          item-title="label"
          item-value="value"
          placeholder="Zahlungsarten wählen"
          multiple
          chips
          closable-chips
          hide-details="auto"
          required
          :rules="[rules.requiredArray]"
        />
        <small>Bei Abrechnung wählt der Kellner eine Art (Popup erscheintnur bei mehreren Zahlungsarten).</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="offer-payment-receipt">Zahlungsbeleg nach Bezahlung anbieten</label>
          <v-switch
            id="offer-payment-receipt"
            v-model="form.offerPaymentReceipt"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">Nach Bezahlung fragt die App, ob ein Zahlungsbeleg gedruckt werden soll.</small>
      </div>
      <TwintQrField
        v-if="showTwintQrSection"
        :edit-mode="editMode"
        :active-id="activeId"
        :has-twint-qr="hasTwintQr"
        :preview-url="twintQrPreviewUrl"
        :busy="twintQrBusy"
        @upload="$emit('upload', $event)"
        @remove="$emit('remove')"
      />
    </section>

    <section class="field-group">
      <h3 class="field-group-title">Config</h3>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="cash-registers-enabled">Kassen</label>
          <v-switch
            id="cash-registers-enabled"
            v-model="form.cashRegistersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">Aktiviert Kassen. Kassen sind stationäre Geräte, an denen Bestellungen aufgenommen werden können.</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="shift-settlement-enabled">Kellner-/Kassenabrechnung</label>
          <v-switch
            id="shift-settlement-enabled"
            v-model="form.shiftSettlementEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          Aktiviert die Schichtabrechnung für Kellner und Kassen. Zu Beginn einer Schicht wird der Kassenbestand erfasst und am Ende
          der Schicht wird abgerechnet.
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="vouchers-enabled">Gutscheine</label>
          <v-switch
            id="vouchers-enabled"
            v-model="form.vouchersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">Aktiviert die Verwendung von Gutscheinen die bei der Bezahlung angerechnet werden können.<br>
        Gutscheine können auch an Kassen verkauft werden.</small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="alternative-printers-enabled">Alternative Drucker</label>
          <v-switch
            id="alternative-printers-enabled"
            v-model="form.alternativePrintersEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          Aktiviert Drucker-Regeln nach Tischbereich oder Abholcode-Präfix pro Station.
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="kitchen-monitors-enabled">Kitchen Monitor</label>
          <v-switch
            id="kitchen-monitors-enabled"
            v-model="form.kitchenMonitorsEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          Aktiviert Kitchen Monitor pro Drucker (Bestellungen werden am Monitor freigegeben statt sofort gedruckt).
        </small>
      </div>
      <div class="toggle-block">
        <div class="toggle-row">
          <label for="discounts-enabled">Rabatte aktivieren</label>
          <v-switch
            id="discounts-enabled"
            v-model="form.discountsEnabled"
            hide-details
            density="compact"
          />
        </div>
        <small class="toggle-hint">
          Aktiviert die Verwendung von Rabatten.<br>
          Rabatte können bei einer Bestellung pro Position oder für die gesamte Bestellung angewendet werden. (% oder Betrag)
        </small>
      </div>
    </section>
  </div>
</template>

<script setup>
import FormLabel from './FormLabel.vue'
import TwintQrField from './TwintQrField.vue'
import { rules } from '../utils/formRules.js'

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
  selectableStatusOptions: {
    type: Array,
    required: true,
  },
  currencyOptions: {
    type: Array,
    required: true,
  },
  paymentModeOptions: {
    type: Array,
    required: true,
  },
  paymentTypeOptions: {
    type: Array,
    required: true,
  },
  showTwintQrSection: {
    type: Boolean,
    default: false,
  },
  editMode: {
    type: Boolean,
    default: false,
  },
  activeId: {
    type: [Number, String],
    default: null,
  },
  hasTwintQr: {
    type: Boolean,
    default: false,
  },
  twintQrPreviewUrl: {
    type: String,
    default: '',
  },
  twintQrBusy: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['upload', 'remove'])

function pad2(n) {
  return String(n).padStart(2, '0')
}

function formatLocalDatetime(value) {
  if (!value || !(value instanceof Date) || Number.isNaN(value.getTime())) {
    return ''
  }
  return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())}T${pad2(value.getHours())}:${pad2(value.getMinutes())}`
}

function parseLocalDatetime(value) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}
</script>

<style scoped>
.field-group {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.field-group-title {
  margin: 0 0 0.65rem;
  font-size: 0.9375rem;
  font-weight: 600;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.toggle-block {
  margin-bottom: 0.65rem;
}

.toggle-block:last-child {
  margin-bottom: 0;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0;
}

.toggle-row label {
  font-size: 0.875rem;
  font-weight: 600;
}

.toggle-hint {
  display: block;
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  opacity: 0.7;
}

small {
  opacity: 0.7;
}

@media (max-width: 1000px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
