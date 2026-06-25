<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop" />
    <div v-if="open" class="sheet twint-qr-sheet" role="dialog" aria-modal="true" aria-labelledby="twint-qr-title">
      <header class="sheet-header">
        <h3 id="twint-qr-title">TWINT</h3>
        <p v-if="amountLabel" class="amount-line">
          <span class="amount-caption">Betrag</span>
          <span class="amount-value">{{ amountLabel }}</span>
        </p>
      </header>
      <div class="qr-wrap">
        <img v-if="dataUrl" :src="dataUrl" alt="TWINT QR-Code" class="qr-image" />
      </div>
      <div class="sheet-actions">
        <button type="button" class="btn primary type-btn" @click="$emit('confirm')">Fertig</button>
        <button type="button" class="btn" @click="$emit('cancel')">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    open?: boolean
    dataUrl?: string
    amountLabel?: string
  }>(),
  { open: false, dataUrl: '', amountLabel: '' },
)

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<style scoped>
.sheet-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 160;
}

.twint-qr-sheet {
  position: fixed;
  inset: 0;
  z-index: 161;
  display: flex;
  flex-direction: column;
  background: var(--card);
  padding: 1rem 1rem calc(1rem + var(--safe-bottom));
}

.sheet-header h3 {
  margin: 0 0 0.25rem;
}

.amount-line {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  margin: 0.5rem 0 0;
}

.amount-caption {
  color: var(--muted);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.amount-value {
  font-size: 2rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.qr-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  padding: 1rem 0;
}

.qr-image {
  max-width: min(92vw, 360px);
  max-height: min(60vh, 360px);
  object-fit: contain;
}

.sheet-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.type-btn {
  width: 100%;
  min-height: 52px;
  font-size: 1.1rem;
  font-weight: 700;
}

.sheet-actions .btn:not(.primary) {
  width: 100%;
  min-height: 44px;
}
</style>
