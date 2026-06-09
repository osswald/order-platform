<template>
  <div class="payment-receipt-profile-fields">
    <v-checkbox
      v-model="model.logo_enabled"
      :label="$t('receipts.printLogo')"
      hide-details
      density="compact"
    />
    <v-checkbox
      v-model="model.show_event_title"
      :label="$t('receipts.showEventTitle')"
      hide-details
      density="compact"
    />
    <p class="muted size-hint">{{ $t('receipts.paymentSizeHint') }}</p>
    <div class="form-field">
      <label>{{ $t('receipts.footerLabel') }}</label>
      <v-textarea
        v-model="model.bottom_line"
        rows="3"
        auto-grow
        :placeholder="$t('receipts.paymentFooterPlaceholder')"
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
