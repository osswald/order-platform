<template>
  <div
    v-if="open"
    class="modem-connecting-overlay"
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <div class="modem-connecting-panel">
      <div class="modem-connecting-spinner" aria-hidden="true" />
      <p class="modem-connecting-text">Connecting...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  open: boolean
}>()
</script>

<style scoped>
.modem-connecting-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.85);
  pointer-events: all;
}

.modem-connecting-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: #f8fafc;
}

.modem-connecting-spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid rgba(248, 250, 252, 0.25);
  border-top-color: #f8fafc;
  border-radius: 50%;
  animation: modem-spin 0.85s linear infinite;
}

.modem-connecting-text {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}

@keyframes modem-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
