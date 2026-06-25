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
      <div v-if="hasStyledPreview(receipt)" class="receipt-preview receipt-preview--styled">
        <div
          v-for="(line, index) in receipt.preview_lines"
          :key="index"
          class="receipt-line"
          :class="lineClass(line)"
          :style="lineStyle(line)"
        >
          <span v-if="line.kind === 'logo'" class="receipt-logo">[Logo]</span>
          <span v-else>{{ line.text }}</span>
        </div>
      </div>
      <pre v-else class="receipt-preview">{{ receipt.preview_text || '(leer)' }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatReceiptTime, useEmulatedReceipts } from '@/composables/useEmulatedReceipts'
import type { EmulatedReceiptSummary, PreviewLine } from '@/types/api'

withDefaults(
  defineProps<{
    compact?: boolean
    showHeader?: boolean
  }>(),
  { compact: false, showHeader: true },
)

const { receipts, loading } = useEmulatedReceipts()

function hasStyledPreview(receipt: EmulatedReceiptSummary) {
  return Array.isArray(receipt.preview_lines) && receipt.preview_lines.length > 0
}

function lineClass(line: PreviewLine) {
  return [
    `receipt-line--align-${line.align || 'left'}`,
    `receipt-line--size-${line.size || 'normal'}`,
    line.bold ? 'receipt-line--bold' : '',
    line.kind === 'logo' ? 'receipt-line--logo' : '',
  ]
}

function lineStyle(line: PreviewLine) {
  if (line.size === 'xlarge' && line.scale) {
    return { fontSize: `calc(1em * ${line.scale} * 0.35)` }
  }
  return undefined
}
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
  /* Match 80 mm thermal paper (~48 chars); keeps center alignment in-column. */
  box-sizing: content-box;
  width: 48ch;
  max-width: 100%;
  overflow-x: auto;
}

.receipt-preview--styled {
  white-space: normal;
}

.receipt-line {
  line-height: 1.25;
  white-space: pre;
}

.receipt-line--align-left {
  text-align: left;
}

.receipt-line--align-center {
  text-align: center;
}

.receipt-line--align-right {
  text-align: right;
}

.receipt-line--size-small {
  font-size: 0.75em;
}

.receipt-line--size-normal {
  font-size: 1em;
}

.receipt-line--size-large {
  font-size: 1.45em;
  font-weight: 600;
}

.receipt-line--size-xlarge {
  font-weight: 700;
}

.receipt-line--bold {
  font-weight: 600;
}

.receipt-line--logo {
  margin: 0.35rem 0;
}

.receipt-logo {
  color: rgba(238, 238, 238, 0.45);
  font-size: 0.85em;
  letter-spacing: 0.04em;
}
</style>
