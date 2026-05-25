<template>
  <div class="event-stammdaten">
    <section class="field-group">
      <h3 class="field-group-title">Basis</h3>
      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Sommerfest 2026" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>Status</label>
          <Select
            v-model="form.status"
            :options="selectableStatusOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Status wählen"
          />
        </div>
        <div class="form-field">
          <label>Währung</label>
          <Select v-model="form.currency" :options="currencyOptions" placeholder="Währung wählen" />
        </div>
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>Start</label>
          <DatePicker
            v-model="form.start"
            showIcon
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            placeholder="Startdatum wählen"
          />
        </div>
        <div class="form-field">
          <label>Ende</label>
          <DatePicker
            v-model="form.end"
            showIcon
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            placeholder="Enddatum wählen"
          />
        </div>
      </div>
    </section>

    <section class="field-group">
      <h3 class="field-group-title">Zahlung</h3>
      <div class="form-field">
        <label>Zahlungsmodus (Pi / Kellner)</label>
        <Select
          v-model="form.paymentMode"
          :options="paymentModeOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Modus wählen"
        />
        <small>Sofort bezahlt = Position als bezahlt beim Absenden; Jetzt bezahlen = vor Abschluss; Später = nach Absenden.</small>
      </div>
      <div class="form-field">
        <label>Zahlungsarten (Pi)</label>
        <MultiSelect
          v-model="form.paymentTypes"
          :options="paymentTypeOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Zahlungsarten wählen"
          display="chip"
          class="w-full"
        />
        <small>Bei Abrechnung wählt der Kellner eine Art (Popup nur bei mehreren).</small>
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
      <div class="toggle-row">
        <label for="cash-registers-enabled">Kassen</label>
        <ToggleSwitch v-model="form.cashRegistersEnabled" inputId="cash-registers-enabled" />
      </div>
      <div class="toggle-row">
        <label for="vouchers-enabled">Gutscheine</label>
        <ToggleSwitch v-model="form.vouchersEnabled" inputId="vouchers-enabled" />
      </div>
    </section>
  </div>
</template>

<script setup>
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import TwintQrField from './TwintQrField.vue'

defineProps({
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
</script>

<style scoped>
.field-group {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.field-group-title {
  margin: 0 0 0.65rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.toggle-row:last-child {
  margin-bottom: 0;
}

.toggle-row label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--p-text-color);
}

small {
  color: var(--p-text-muted-color);
}

:deep(.p-inputtext),
:deep(.p-select),
:deep(.p-datepicker),
:deep(.p-multiselect) {
  width: 100%;
}

@media (max-width: 1000px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
