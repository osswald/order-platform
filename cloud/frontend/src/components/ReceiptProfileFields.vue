<template>
  <div class="receipt-profile-fields">
    <v-checkbox
      v-model="model.logo_enabled"
      label="Logo drucken"
      hide-details
      density="compact"
    />
    <v-checkbox
      v-model="model.show_event_title"
      label="Event-Titel anzeigen"
      hide-details
      density="compact"
    />
    <v-checkbox
      v-if="showPriceOption"
      v-model="model.show_price"
      label="Preise anzeigen"
      hide-details
      density="compact"
    />
    <div class="form-field">
      <label>{{ pickupLabel }} — Schriftgröße</label>
      <v-select
        v-model="model.size_table_or_pickup"
        :items="tableSizeOptions"
        item-title="label"
        item-value="value"
        density="compact"
        hide-details
      />
    </div>
    <div class="form-field">
      <label>Bestellpositionen — Schriftgröße</label>
      <v-select
        v-model="model.size_order_lines"
        :items="lineSizeOptions"
        item-title="label"
        item-value="value"
        density="compact"
        hide-details
      />
    </div>
    <div class="form-field">
      <label>Fußzeile (zentriert, mehrzeilig)</label>
      <v-textarea
        v-model="model.bottom_line"
        rows="3"
        auto-grow
        placeholder="Optional"
        density="compact"
        hide-details
      />
    </div>
  </div>
</template>

<script setup>
const model = defineModel({ type: Object, required: true })

defineProps({
  pickupLabel: { type: String, default: 'Tisch / Pickup' },
  /** Kitchen station slips never print prices; only shown for customer pickup profile. */
  showPriceOption: { type: Boolean, default: true },
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
</style>
