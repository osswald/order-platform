<template>
  <div>
    <h1>Bluetooth Drucker</h1>
    <p class="muted">Auswahl wird nur auf diesem Android-Gerät gespeichert.</p>

    <div v-if="!available" class="card">
      <p>Diese Ansicht funktioniert nur in der Android-App.</p>
    </div>

    <template v-else>
      <div class="card">
        <p>
          Berechtigung:
          <strong>{{ permissionLabel }}</strong>
        </p>
        <button type="button" class="btn" @click="requestPermissions">Berechtigung anfragen</button>
      </div>

      <div class="card">
        <h2 class="card-title">Belegbreite</h2>
        <p class="muted">Breite für Kellner-Belege auf diesem Gerät (Zahlungsbeleg per Bluetooth).</p>
        <div class="paper-width-options">
          <label v-for="opt in paperWidthOptions" :key="opt.value" class="paper-width-option">
            <input
              type="radio"
              name="paper_width"
              :value="opt.value"
              :checked="paperWidth === opt.value"
              @change="onPaperWidthChange(opt.value)"
            />
            {{ opt.label }}
          </label>
        </div>
      </div>

      <div class="card">
        <div class="row">
          <button type="button" class="btn" @click="loadPrinters">Gekoppelte Drucker laden</button>
          <button type="button" class="btn primary" :disabled="busy || !selectedAddress" @click="testPrint">
            Testbeleg drucken
          </button>
        </div>

        <p v-if="!printers.length" class="muted" style="margin-top: 0.75rem">
          Keine gekoppelten Bluetooth-Drucker geladen.
        </p>

        <div v-for="printer in printers" :key="printer.address" class="printer-row">
          <label>
            <input
              type="radio"
              name="printer"
              :value="printer.address"
              :checked="printer.address === selectedAddress"
              @change="selectPrinter(printer)"
            />
            <strong>{{ printer.name || printer.address }}</strong>
            <span class="muted">{{ printer.address }}</span>
          </label>
        </div>
      </div>

      <p v-if="message" :class="messageType === 'ok' ? 'ok' : 'err'">{{ message }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useEventContext } from '../composables/useEventContext'
import {
  getSelectedPrinter,
  isAndroidPrinterAvailable,
  listPairedPrinters,
  permissionStatus,
  printTestReceipt,
  requestPrinterPermissions,
  setSelectedPrinter,
} from '../utils/androidPrinter'
import {
  getReceiptPaperWidth,
  RECEIPT_PAPER_WIDTH_OPTIONS,
  setReceiptPaperWidth,
} from '../utils/receiptPaperWidth'

const { event } = useEventContext()
const available = computed(() => isAndroidPrinterAvailable())
const printers = ref([])
const selectedAddress = ref('')
const permission = ref(null)
const busy = ref(false)
const message = ref('')
const messageType = ref('ok')
const paperWidthOptions = RECEIPT_PAPER_WIDTH_OPTIONS
const paperWidth = ref(getReceiptPaperWidth())

const permissionLabel = computed(() => {
  if (!permission.value) return 'unbekannt'
  return permission.value.granted ? 'erteilt' : 'fehlt'
})

function show(msg, type = 'ok') {
  message.value = msg
  messageType.value = type
}

function refreshPermission() {
  permission.value = permissionStatus()
}

function refreshSelected() {
  const result = getSelectedPrinter()
  if (result.ok) selectedAddress.value = result.address || ''
}

function requestPermissions() {
  const result = requestPrinterPermissions()
  refreshPermission()
  show(result.ok ? 'Berechtigung angefragt.' : result.error || 'Berechtigung fehlgeschlagen.', result.ok ? 'ok' : 'err')
}

function loadPrinters() {
  refreshPermission()
  const result = listPairedPrinters()
  if (!result.ok) {
    show(result.error || 'Drucker konnten nicht geladen werden.', 'err')
    return
  }
  printers.value = result.printers
  refreshSelected()
}

function onPaperWidthChange(value) {
  setReceiptPaperWidth(value)
  paperWidth.value = value
  show('Belegbreite gespeichert.', 'ok')
}

function selectPrinter(printer) {
  const result = setSelectedPrinter(printer.address)
  if (!result.ok) {
    show(result.error || 'Drucker konnte nicht gespeichert werden.', 'err')
    return
  }
  selectedAddress.value = printer.address
  show(`${printer.name || printer.address} gespeichert.`, 'ok')
}

async function testPrint() {
  busy.value = true
  try {
    await printTestReceipt(event.value?.id)
    show('Testbeleg gedruckt.', 'ok')
  } catch (e) {
    show(e.message || 'Testbeleg fehlgeschlagen.', 'err')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  if (!available.value) return
  refreshPermission()
  loadPrinters()
})
</script>

<style scoped>
.card-title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
}
.paper-width-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.paper-width-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.printer-row {
  padding: 0.75rem 0;
  border-top: 1px solid var(--border);
}
.printer-row label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.ok {
  color: var(--ok);
}
.err {
  color: var(--danger);
}
</style>
