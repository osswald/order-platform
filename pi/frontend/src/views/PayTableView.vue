<template>
  <SplitPaySettleScreen
    :header-table="table"
    empty-text="Keine offenen Posten auf diesem Tisch."
    settled-toast="Tisch vollständig abgerechnet."
    :load-summary="loadSummary"
    :settle-partial-path="() => `/v1/tables/${table}/settle-partial`"
    :actions-from-table="table"
    :voucher-row-label="(name: string) => `Gutschein: ${name}`"
    @back="goHub"
    @settled="goHub"
    @load-error="goHub"
    @gone="goHub"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventContext } from '@/composables/useEventContext'
import { api } from '@/api'
import type { AccountSummaryResponse } from '@/types/api'
import SplitPaySettleScreen from '@/components/SplitPaySettleScreen.vue'

const route = useRoute()
const router = useRouter()
const { event } = useEventContext()
const table = computed(() => parseInt(String(route.query.table), 10))

async function loadSummary(): Promise<AccountSummaryResponse | { line_groups: [] }> {
  const ev = event.value
  if (!ev || !table.value) return { line_groups: [] }
  return api<AccountSummaryResponse>(`/v1/tables/${table.value}?event_id=${ev.id}`)
}

function goHub() {
  router.push({ name: 'hub' })
}
</script>
