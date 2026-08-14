<template>
  <div class="customer-display">
    <section v-if="payload.state === 'submitted'" class="pickup-done">
      <p>Danke!</p>
      <div v-if="displayPickupBadges.length" class="pickup-badges" aria-label="Pickup">
        <span v-for="badge in displayPickupBadges" :key="badge.code" class="pickup-badge">
          <span class="pickup-badge-code">{{ badge.code }}</span>
          <span v-if="badge.stationName" class="pickup-badge-station">{{ badge.stationName }}</span>
        </span>
      </div>
      <span v-if="displayPickupBadges.length">{{ abholbonText }}</span>
    </section>

    <section v-else-if="payload.state === 'sumup_connected'" class="sumup-panel">
      <p class="sumup-instruction">Bitte Anweisungen am Zahlungsterminal folgen.</p>
    </section>

    <section v-else-if="payload.state === 'twint' || payload.show_twint" class="twint-panel">
      <div class="twint-info">
        <h2>TWINT</h2>
        <p class="twint-amount">{{ formatMoney(payload.total_cents || 0, currency) }}</p>
        <p v-if="!payload.twint_qr_data_url" class="muted">Bitte mit TWINT bezahlen.</p>
      </div>
      <div v-if="payload.twint_qr_data_url" class="twint-qr">
        <img :src="payload.twint_qr_data_url" alt="TWINT QR-Code" class="qr-image" />
      </div>
    </section>

    <section v-else-if="payload.state === 'ordering'" class="order-preview">
      <div
        ref="orderBodyRef"
        class="display-order-body"
        :class="{ 'display-order-body--scrolled': orderBodyScrolled }"
        @scroll="onOrderBodyScroll"
      >
        <h2>Ihre Bestellung</h2>
        <p v-if="!lines.length" class="muted">Noch keine Artikel.</p>
        <ul v-else>
          <li v-for="line in lines" :key="line.lineId || lineKey(line)">
            <span class="line-label">{{ Math.max(1, Number(line.qty) || 1) }}x {{ lineLabel(line) }}</span>
            <span class="line-price">{{ lineTotal(line) }}</span>
            <span
              v-for="add in additionLabelsFor(line)"
              :key="add.id"
              class="addition"
            >+ {{ add.name }}</span>
          </li>
          <li v-for="v in voucherLines" :key="v.key" class="voucher-line">
            <span class="line-label">{{ v.label }}</span>
            <span class="line-price">−{{ formatMoney(v.applied_cents ?? v.appliedCents ?? 0, currency) }}</span>
          </li>
        </ul>
      </div>
      <footer class="order-total">
        <span>Total</span>
        <strong>{{ formatMoney(payload.total_cents || 0, currency) }}</strong>
      </footer>
    </section>

    <section v-else class="idle-screen">
      <div v-if="screensaverUrls.length" class="screensaver">
        <img
          :src="screensaverUrls[screensaverIndex % screensaverUrls.length]"
          alt=""
          class="screensaver-image"
          :class="{ 'screensaver-image--greyscale': screensaverGreyscale }"
        />
      </div>
      <p v-else class="welcome">Herzlich Willkommen</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { RegisterDisplayPayload } from '@/types/api'
import type { CartLine } from '@/types/cart'
import { api } from '@/api'
import { buildWsUrl, getApiBase } from '@/api/base'
import { useEventContext } from '@/composables/useEventContext'
import { abholbonFooterText, pickupBadgesForDisplay } from '@/utils/customerDisplayPickup'
import { formatMoney, lineTotalCents, type MoneyLine } from '@/utils/money'
import { cartLineLabelForEvent, lineAdditionLabels } from '@/utils/bundleHelpers'

interface VoucherDisplayLine {
  key?: string
  label?: string
  applied_cents?: number
  appliedCents?: number
}

type DisplayPayload = RegisterDisplayPayload & {
  show_twint?: boolean
  twint_qr_data_url?: string | null
  pickup_code?: string | null
  pickup_codes?: string[] | null
  pickups?: Array<{
    pickup_code?: string | null
    station_uuid?: string | null
    station_name?: string | null
  }> | null
  voucher_lines?: VoucherDisplayLine[]
  lines?: Array<CartLine & { display_label?: string }>
}

const POLL_MS = 5000
const SCREENSAVER_DWELL_MS = 9000

const route = useRoute()
const payload = ref<DisplayPayload>({ state: 'idle' })
const orderBodyRef = ref<HTMLElement | null>(null)
const orderBodyScrolled = ref(false)
const screensaverUrls = ref<string[]>([])
const screensaverGreyscale = ref(false)
const screensaverIndex = ref(0)
let pollTimer: ReturnType<typeof setInterval> | null = null
let screensaverTimer: ReturnType<typeof setInterval> | null = null
let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
let disposed = false
let lastCartSignature = ''
let wsConnected = false

const { event, currency } = useEventContext()
const registerUuid = computed(() => String(route.params.registerUuid || ''))
const lines = computed(() => payload.value.lines || [])
const voucherLines = computed(() => payload.value.voucher_lines || [])
const articles = computed(() => event.value?.articles || {})
const displayPickupBadges = computed(() => pickupBadgesForDisplay(payload.value, event.value))
const abholbonText = computed(() => abholbonFooterText(displayPickupBadges.value.length))

function lineKey(line: CartLine & { display_label?: string }) {
  if (line?.lineId) return line.lineId
  if (line?.kind === 'voucher_sale') return `v-${line.voucher_definition_uuid}-${line.qty}`
  return `${line.article_id}-${line.qty}`
}

function lineLabel(line: CartLine & { display_label?: string }) {
  if (line?.display_label) return line.display_label
  return cartLineLabelForEvent(line, event.value)
}

function toMoneyLine(line: CartLine & { display_label?: string }): MoneyLine {
  return {
    article_id: Number(line.article_id),
    qty: line.qty,
    note: line.note,
    additions: line.additions,
    discount: line.discount ?? undefined,
  }
}

function lineTotal(line: CartLine & { display_label?: string }) {
  return formatMoney(lineTotalCents(toMoneyLine(line), articles.value, event.value), currency.value)
}

function additionLabelsFor(line: CartLine & { display_label?: string }) {
  const moneyLine = toMoneyLine(line)
  return lineAdditionLabels(
    { article_id: moneyLine.article_id!, additions: moneyLine.additions },
    articles.value,
  )
}

function cartScrollSignature() {
  const cartLines = payload.value.lines || []
  const vouchers = payload.value.voucher_lines || []
  const last = cartLines[cartLines.length - 1]
  const lastVoucher = vouchers[vouchers.length - 1]
  const lastId = last ? last.lineId || lineKey(last) : ''
  const lastQty = last ? Math.max(1, Number(last.qty) || 1) : 0
  const lastVoucherKey = lastVoucher ? String(lastVoucher.key || '') : ''
  return `${cartLines.length}|${lastId}|${lastQty}|${vouchers.length}|${lastVoucherKey}`
}

function scrollToLatest() {
  const el = orderBodyRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

function onOrderBodyScroll() {
  const el = orderBodyRef.value
  orderBodyScrolled.value = Boolean(el && el.scrollTop > 4)
}

function maybeScrollToLatest() {
  if (payload.value.state !== 'ordering') return
  const sig = cartScrollSignature()
  if (sig === lastCartSignature) return
  lastCartSignature = sig
  const cartLines = payload.value.lines || []
  const vouchers = payload.value.voucher_lines || []
  if (!cartLines.length && !vouchers.length) return
  nextTick(() => {
    scrollToLatest()
    onOrderBodyScroll()
  })
}

function applyPayload(next: DisplayPayload) {
  payload.value = next || { state: 'idle' }
}

watch(
  () => [payload.value.state, payload.value.lines, payload.value.voucher_lines],
  () => {
    if (payload.value.state !== 'ordering') {
      lastCartSignature = ''
      orderBodyScrolled.value = false
      return
    }
    maybeScrollToLatest()
  },
)

async function loadDisplay() {
  if (!event.value?.id || !registerUuid.value) return
  try {
    const data = await api<{ payload?: DisplayPayload }>(
      `/v1/registers/${encodeURIComponent(registerUuid.value)}/display?event_id=${encodeURIComponent(event.value.id)}`,
    )
    applyPayload(data?.payload || { state: 'idle' })
  } catch {
    applyPayload({ state: 'idle' })
  }
}

async function loadScreensaverUrls() {
  if (!event.value?.id) {
    screensaverUrls.value = []
    screensaverGreyscale.value = false
    return
  }
  try {
    const data = await api<{ images?: Array<{ sha256: string }>; greyscale?: boolean }>(
      `/v1/screensaver/images?event_id=${encodeURIComponent(event.value.id)}`,
    )
    const hashes = (data?.images || []).map((i) => String(i.sha256 || '').trim()).filter(Boolean)
    const base = getApiBase().replace(/\/$/, '')
    screensaverUrls.value = hashes.map((h) => `${base}/v1/screensaver/${encodeURIComponent(h)}`)
    screensaverGreyscale.value = Boolean(data?.greyscale)
    screensaverIndex.value = 0
  } catch {
    screensaverUrls.value = []
    screensaverGreyscale.value = false
  }
}

function stopScreensaverRotation() {
  if (screensaverTimer) {
    clearInterval(screensaverTimer)
    screensaverTimer = null
  }
}

function startScreensaverRotation() {
  stopScreensaverRotation()
  if (screensaverUrls.value.length < 2) return
  screensaverTimer = setInterval(() => {
    screensaverIndex.value = (screensaverIndex.value + 1) % screensaverUrls.value.length
  }, SCREENSAVER_DWELL_MS)
}

watch(
  () => [payload.value.state, screensaverUrls.value.length] as const,
  ([state, count]) => {
    if (state === 'idle' || state == null || state === '') {
      if (count > 0) startScreensaverRotation()
      else stopScreensaverRotation()
    } else {
      stopScreensaverRotation()
    }
  },
)

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (!wsConnected) void loadDisplay()
  }, POLL_MS)
}

function clearWsReconnect() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
}

function closeWs() {
  clearWsReconnect()
  if (ws) {
    ws.onopen = null
    ws.onmessage = null
    ws.onerror = null
    ws.onclose = null
    try {
      ws.close()
    } catch {
      /* ignore */
    }
    ws = null
  }
  wsConnected = false
}

function connectWs() {
  if (disposed || !event.value?.id || !registerUuid.value) return
  closeWs()
  const path =
    `/v1/registers/${encodeURIComponent(registerUuid.value)}/display/ws` +
    `?event_id=${encodeURIComponent(event.value.id)}`
  const url = buildWsUrl(getApiBase(), path)
  try {
    ws = new WebSocket(url)
  } catch {
    wsConnected = false
    scheduleWsReconnect()
    return
  }
  ws.onopen = () => {
    wsConnected = true
  }
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(String(ev.data || '{}')) as { payload?: DisplayPayload }
      applyPayload(data?.payload || { state: 'idle' })
    } catch {
      /* ignore malformed */
    }
  }
  ws.onerror = () => {
    /* onclose handles reconnect */
  }
  ws.onclose = () => {
    wsConnected = false
    ws = null
    if (!disposed) {
      void loadDisplay()
      scheduleWsReconnect()
    }
  }
}

function scheduleWsReconnect() {
  clearWsReconnect()
  if (disposed) return
  wsReconnectTimer = setTimeout(() => {
    wsReconnectTimer = null
    connectWs()
  }, 1500)
}

onMounted(() => {
  disposed = false
  void loadDisplay()
  void loadScreensaverUrls()
  connectWs()
  startPolling()
})

onUnmounted(() => {
  disposed = true
  stopPolling()
  stopScreensaverRotation()
  closeWs()
})

watch(
  () => [event.value?.id, registerUuid.value],
  () => {
    void loadDisplay()
    void loadScreensaverUrls()
    connectWs()
  },
)
</script>

<style scoped>
.customer-display {
  box-sizing: border-box;
  height: 100dvh;
  overflow: hidden;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  display: flex;
  flex-direction: column;
  background: #101418;
  color: #fff;
}
.muted {
  color: #b8c1cc;
}
.order-preview,
.pickup-done,
.twint-panel,
.sumup-panel,
.idle-screen {
  flex: 1;
  min-height: 0;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 1.5rem;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  background: rgba(255, 255, 255, 0.06);
}
.idle-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
  padding: 0;
}
.welcome {
  margin: 0;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  font-size: clamp(2rem, 8vw, 4.5rem);
  font-weight: 600;
  line-height: 1.2;
}
.screensaver {
  width: 100%;
  height: 100%;
}
.screensaver-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.screensaver-image--greyscale {
  filter: grayscale(1);
}
.order-preview {
  display: flex;
  flex-direction: column;
}
.display-order-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overflow-anchor: auto;
  scrollbar-gutter: stable;
}
.display-order-body ul {
  width: 100%;
}
.display-order-body--scrolled::before {
  content: '';
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1;
  display: block;
  height: 2rem;
  margin-bottom: -2rem;
  pointer-events: none;
  background: linear-gradient(to bottom, rgba(22, 26, 31, 0.98), transparent);
}
.order-preview h2,
.twint-panel h2 {
  margin-top: 0;
}
ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 1rem;
  row-gap: 0.35rem;
  padding: 0.8rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  font-size: clamp(1rem, 2.5vw, 1.75rem);
}
.line-label {
  min-width: 0;
}
.line-price {
  text-align: right;
  white-space: nowrap;
}
.addition {
  grid-column: 1 / -1;
  font-size: 0.75em;
  color: #b8c1cc;
}
.voucher-line {
  color: #86efac;
}
.order-total {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 2px solid rgba(255, 255, 255, 0.24);
  font-size: clamp(1.5rem, 4vw, 2.75rem);
}
.order-total strong {
  font-size: clamp(1.8rem, 5vw, 3.25rem);
}
.twint-panel {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 1rem;
}
.twint-info {
  flex: 0 0 38%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.twint-amount {
  font-size: clamp(1.75rem, 5vw, 3.5rem);
  font-weight: 700;
  margin: 0.5rem 0 0;
}
.twint-qr {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
.qr-image {
  max-height: calc(100dvh - 2rem);
  max-width: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}
.sumup-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.sumup-instruction {
  margin: 0;
  font-size: clamp(1.6rem, 4.5vw, 3rem);
  font-weight: 600;
  line-height: 1.3;
  max-width: 18em;
}
.pickup-done {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: 1rem;
}
.pickup-done p {
  font-size: clamp(1.8rem, 4vw, 3rem);
  margin: 0;
}
.pickup-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem 1rem;
}
.pickup-badge {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 3.5rem;
  padding: 0.45rem 0.95rem 0.4rem;
  border: 2px solid rgba(255, 255, 255, 0.55);
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.1);
  line-height: 1.1;
}
.pickup-badge-code {
  font-size: clamp(2.5rem, 10vw, 7rem);
  font-weight: 700;
  line-height: 1.1;
}
.pickup-badge-station {
  margin-top: 0.15rem;
  font-size: clamp(0.85rem, 2.2vw, 1.4rem);
  font-weight: 600;
  line-height: 1.2;
  opacity: 0.85;
}
.pickup-done > span {
  font-size: clamp(1.2rem, 3vw, 2rem);
}

@media (orientation: portrait) {
  .twint-panel {
    flex-direction: column;
    justify-content: center;
  }
  .twint-info {
    flex: 0 0 auto;
    width: 100%;
    text-align: center;
  }
  .twint-qr {
    flex: 1;
    width: 100%;
  }
}
</style>
