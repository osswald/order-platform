<template>
  <SplitPaySettleScreen
    :header-title="headerTitle"
    empty-text="Noch keine Posten."
    settled-toast="Sammelrechnung vollständig abgerechnet."
    :load-summary="loadSummary"
    :settle-partial-path="() => `/v1/collective-bills/${billId}/settle-partial`"
    actions-voucher-only
    @back="goBack"
    @settled="goBack"
    @load-error="goBack"
    @gone="goBack"
  >
    <template #empty-extra>
      <p v-if="billName" class="muted empty-assign-hint">
        Am Tisch ☰ → Sammelrechnung → «{{ billName }}» Positionen zuordnen.
      </p>
    </template>
  </SplitPaySettleScreen>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventContext } from '@/composables/useEventContext'
import { api } from '@/api'
import type { AccountSummaryResponse } from '@/types/api'
import SplitPaySettleScreen from '@/components/SplitPaySettleScreen.vue'

type CollectiveSummary = AccountSummaryResponse & { name?: string }

const route = useRoute()
const router = useRouter()
const billName = ref('')
const billId = computed(() => parseInt(String(route.query.id), 10))
const { event } = useEventContext()
const headerTitle = computed(() =>
  billName.value ? `Sammelrechnung: ${billName.value}` : 'Sammelrechnung',
)

async function loadSummary(): Promise<CollectiveSummary | { line_groups: [] }> {
  const ev = event.value
  if (!ev || !billId.value) return { line_groups: [] }
  const data = await api<CollectiveSummary>(`/v1/collective-bills/${billId.value}?event_id=${ev.id}`)
  billName.value = data.name || ''
  return data
}

function goBack() {
  router.push({ name: 'collective-open' })
}
</script>

<style scoped>
.empty-assign-hint {
  margin: 0.75rem 0 1rem;
  font-size: 0.95rem;
  line-height: 1.4;
  max-width: 22rem;
}
</style>
