<template>
  <div class="receipt-profile-fields">
    <div class="check-row">
      <Checkbox v-model="model.logo_enabled" :binary="true" inputId="logo-enabled" />
      <label for="logo-enabled">Logo drucken</label>
    </div>
    <div class="check-row">
      <Checkbox v-model="model.show_event_title" :binary="true" inputId="show-title" />
      <label for="show-title">Event-Titel anzeigen</label>
    </div>
    <div class="check-row">
      <Checkbox v-model="model.show_price" :binary="true" inputId="show-price" />
      <label for="show-price">Preise anzeigen</label>
    </div>
    <div class="form-field">
      <label>{{ pickupLabel }} — Schriftgröße</label>
      <Select
        v-model="model.size_table_or_pickup"
        :options="tableSizeOptions"
        optionLabel="label"
        optionValue="value"
      />
    </div>
    <div class="form-field">
      <label>Bestellpositionen — Schriftgröße</label>
      <Select
        v-model="model.size_order_lines"
        :options="lineSizeOptions"
        optionLabel="label"
        optionValue="value"
      />
    </div>
    <div class="form-field">
      <label>Fußzeile (zentriert, mehrzeilig)</label>
      <Textarea v-model="model.bottom_line" rows="3" autoResize placeholder="Optional" />
    </div>
  </div>
</template>

<script setup>
import Checkbox from 'primevue/checkbox'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

const model = defineModel({ type: Object, required: true })

defineProps({
  pickupLabel: { type: String, default: 'Tisch / Pickup' },
})

const tableSizeOptions = [
  { label: 'Normal', value: 'normal' },
  { label: 'Groß', value: 'large' },
  { label: 'Sehr groß', value: 'xlarge' },
]

const lineSizeOptions = [
  { label: 'Normal', value: 'normal' },
  { label: 'Groß', value: 'large' },
]
</script>

<style scoped>
.receipt-profile-fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
