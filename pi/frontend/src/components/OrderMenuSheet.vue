<template>
  <Teleport to="body">
    <div v-if="open" class="sheet-backdrop sheet-backdrop--actions" @click.self="close" />
    <div v-if="open" class="sheet sheet--actions" role="dialog" aria-modal="true">
      <header class="sheet-header">
        <h3>Bestellung</h3>
      </header>
      <div class="menu-actions">
        <button
          v-if="showOrderDiscount"
          type="button"
          class="btn menu-btn"
          @click="$emit('order-discount')"
        >
          Rabatt auf Bestellung
        </button>
        <button
          v-if="showVoucher"
          type="button"
          class="btn menu-btn"
          @click="$emit('redeem-voucher')"
        >
          Gutschein einlösen
        </button>
      </div>
      <div class="sheet-footer">
        <button type="button" class="btn" @click="close">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    open?: boolean
    showOrderDiscount?: boolean
    showVoucher?: boolean
  }>(),
  { open: false, showOrderDiscount: false, showVoucher: false },
)

const emit = defineEmits<{
  close: []
  'order-discount': []
  'redeem-voucher': []
}>()

function close() {
  emit('close')
}
</script>

<style scoped>
.sheet-backdrop--actions {
  z-index: 200;
}

.sheet--actions {
  z-index: 201;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.sheet-header h3 {
  margin: 0;
  font-size: 1rem;
}

.menu-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.menu-btn {
  width: 100%;
  min-height: 52px;
  font-size: 1.05rem;
  font-weight: 600;
  touch-action: manipulation;
}

.sheet-footer {
  margin-top: 0.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.sheet-footer .btn {
  width: 100%;
  min-height: 48px;
  touch-action: manipulation;
}
</style>
