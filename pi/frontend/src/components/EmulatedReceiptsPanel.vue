<template>
  <div class="emulated-receipts-panel" :class="{ 'emulated-receipts-panel--compact': compact }">
    <header v-if="showHeader" class="emulated-receipts-header">
      <h2>Emulierte Belege</h2>
      <p class="muted">Druckausgaben erscheinen hier statt auf Papier.</p>
    </header>

    <p v-if="loading && !receipts.length" class="muted">Laden…</p>
    <p v-else-if="!receipts.length" class="muted">Noch keine Belege.</p>

    <div v-for="receipt in receipts" :key="receipt.id" class="receipt-card">
      <div class="receipt-meta">
        <strong>{{ receipt.station_name || receipt.job_kind || 'Beleg' }}</strong>
        <span v-if="receipt.created_at" class="muted small">{{ formatReceiptTime(receipt.created_at) }}</span>
      </div>
      <pre class="receipt-preview">{{ receipt.preview_text || '(leer)' }}</pre>
    </div>
  </div>
</template>

<script setup>
import { formatReceiptTime, useEmulatedReceipts } from '../composables/useEmulatedReceipts'

defineProps({
  compact: { type: Boolean, default: false },
  showHeader: { type: Boolean, default: true },
})

const { receipts, loading } = useEmulatedReceipts()
</script>

<style scoped>
.emulated-receipts-panel {
  padding: 0.75rem 1rem 1rem;
}

.emulated-receipts-panel--compact {
  padding: 0;
}

.emulated-receipts-header {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--bg, #0f172a);
  padding-bottom: 0.75rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}

.emulated-receipts-header h2 {
  margin: 0 0 0.25rem;
  font-size: 1.05rem;
}

.receipt-card {
  margin-bottom: 0.75rem;
}

.receipt-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.receipt-preview {
  margin: 0;
  padding: 0.75rem;
  background: #111;
  color: #eee;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  overflow-x: auto;
}
</style>
