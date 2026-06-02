<template>
  <div class="payment-receipt-profile-fields">
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
    <p class="muted size-hint">Schriftgröße: klein (für kompakte Zahlungsbelege).</p>
    <div class="form-field">
      <label>Fußzeile (zentriert, mehrzeilig)</label>
      <v-textarea
        v-model="model.bottom_line"
        rows="3"
        auto-grow
        placeholder="Optional — leer = «Danke!»"
        density="compact"
        hide-details
      />
    </div>
  </div>
</template>

<script setup>
const model = defineModel({ type: Object, required: true })
</script>

<style scoped>
.payment-receipt-profile-fields {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.size-hint {
  margin: 0;
  font-size: 0.85rem;
}
</style>
