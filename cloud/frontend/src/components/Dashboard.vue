<template>
  <div class="dashboard vq-page">
    <div class="dashboard-header">
      <h1>{{ $t('dashboard.title') }}</h1>
      <p v-if="summary" class="subtitle">
        {{ $t('dashboard.subtitleFor', { name: summary.organisation_name }) }}
      </p>
      <p v-else class="subtitle">{{ $t('dashboard.welcome') }}</p>
    </div>

    <p v-if="activeOrganisationId == null" class="empty-hint">
      {{ $t('common.noOrganisation') }}
    </p>

    <p v-else-if="loadError" class="error">{{ loadError }}</p>

    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>

    <template v-else-if="summary">
      <div class="toolbar">
        <v-btn
          variant="outlined"
          type="button"
          prepend-icon="mdi-refresh"
          :disabled="loading"
          @click="reload"
        >
          {{ $t('common.refresh') }}
        </v-btn>
      </div>

      <div class="cards-grid">
        <div class="stat-card">
          <div class="card-icon"><v-icon icon="mdi-calendar" /></div>
          <div class="card-content">
            <h3>{{ $t('dashboard.events') }}</h3>
            <p class="card-value">{{ summary.events_total }}</p>
            <p class="card-detail">{{ eventsDetail }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><v-icon icon="mdi-card-account-details" /></div>
          <div class="card-content">
            <h3>{{ $t('dashboard.waiters') }}</h3>
            <p class="card-value">{{ summary.catalog.waiters }}</p>
            <p class="card-detail">{{ $t('dashboard.forOrganisation') }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><v-icon icon="mdi-tag-multiple" /></div>
          <div class="card-content">
            <h3>{{ $t('dashboard.articles') }}</h3>
            <p class="card-value">{{ summary.catalog.articles }}</p>
            <p class="card-detail">
              {{ $t('dashboard.categories', { count: summary.catalog.categories }) }}
            </p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><v-icon icon="mdi-calendar-plus" /></div>
          <div class="card-content">
            <h3>{{ $t('dashboard.lendings') }}</h3>
            <p class="card-value">{{ summary.lendings.current }}</p>
            <p class="card-detail">
              {{ $t('dashboard.planned', { count: summary.lendings.planned }) }}
            </p>
          </div>
        </div>
      </div>

      <div class="quick-links">
        <RouterLink :to="routeTo('events')" class="quick-link">{{ $t('nav.events') }}</RouterLink>
        <RouterLink :to="routeTo('waiters')" class="quick-link">{{ $t('nav.waiters') }}</RouterLink>
        <RouterLink :to="routeTo('articles')" class="quick-link">{{ $t('nav.articles') }}</RouterLink>
        <RouterLink :to="routeTo('appliance-lendings')" class="quick-link">
          {{ $t('nav.applianceLendings') }}
        </RouterLink>
      </div>

      <DashboardOnboardingCard
        v-if="summary.onboarding && activeOrganisationId != null"
        :organisation-id="activeOrganisationId"
        :onboarding="summary.onboarding"
        :can-access-organisation-settings="canAccessOrganisationSettings"
        @dismissed="reload"
        @updated="reload"
      />

      <div class="content-section">
        <div class="section-card">
          <h2>{{ $t('dashboard.eventsByStatus') }}</h2>
          <div class="status-chips">
            <v-chip
              v-for="status in statusOrder"
              :key="status"
              :color="eventStatusColor(status)"
              variant="tonal"
              size="small"
            >
              {{ statusLabel(status) }}: {{ summary.events_by_status[status] || 0 }}
            </v-chip>
          </div>
          <p v-if="summary.running_events_count > 0" class="running-hint">
            <v-icon icon="mdi-play-circle" size="small" />
            {{ $t('dashboard.runningEventsHint', { count: summary.running_events_count }) }}
          </p>
        </div>

        <div class="section-card">
          <h2>{{ $t('dashboard.attention') }}</h2>
          <div v-if="summary.attention.length" class="activity-list">
            <RouterLink
              v-for="(item, idx) in summary.attention"
              :key="`${item.type}-${item.event_id}-${idx}`"
              :to="routeTo('events')"
              class="activity-item"
            >
              <span class="activity-badge" :class="attentionClass(item.type)">
                <v-icon
                  :icon="attentionIcon(item.type)"
                  size="small"
                  class="activity-badge-icon"
                />
              </span>
              <div class="activity-text">
                <p class="activity-title">{{ attentionMessage(item) }}</p>
                <p class="activity-time">{{ item.event_name }}</p>
              </div>
            </RouterLink>
          </div>
          <p v-else class="muted">{{ $t('dashboard.attentionEmpty') }}</p>
        </div>
      </div>

      <div v-if="hasSalesSection" class="section-card sales-section">
        <h2>{{ $t('dashboard.salesTitle') }}</h2>
        <p class="muted small footnote">
          {{ $t('dashboard.salesFootnote') }}
        </p>

        <div class="summary-grid">
          <div class="summary-card">
            <span class="summary-label">{{ $t('dashboard.salesOrders') }}</span>
            <span class="summary-value">{{ summary.sales.totals.distinct_orders_count }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('dashboard.salesLineItems') }}</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.line_cents) }} {{ summary.sales.currency }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('dashboard.salesPaid') }}</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.paid_cents) }} {{ summary.sales.currency }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('dashboard.salesOpen') }}</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.open_cents) }} {{ summary.sales.currency }}</span>
          </div>
        </div>

        <h3 class="subsection-title">{{ $t('dashboard.salesEventsTitle') }}</h3>
        <p v-if="!summary.sales.by_event.length" class="muted">{{ $t('dashboard.salesNoEvents') }}</p>
        <VqDataTable
          v-else
          :headers="salesEventHeaders"
          :items="summary.sales.by_event"
          item-value="event_id"
          hide-default-footer
          class="vq-data-table list-table"
        >
          <template #item.period="{ item }">{{ formatEventDateRange(item.start, item.end) }}</template>
          <template #item.distinct_orders_count="{ item }">{{ item.distinct_orders_count }}</template>
          <template #item.line_cents="{ item }">{{ formatAmount(item.line_cents) }}</template>
          <template #item.open_cents="{ item }">{{ formatAmount(item.open_cents) }}</template>
        </VqDataTable>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { useDashboardSummary } from '../composables/useDashboardSummary'
import { attentionMessage, eventsStatDetail, formatEventDateRange, statusLabel } from '../utils/dashboardMetrics'
import { eventStatusColor } from '../utils/eventStatus'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'
import DashboardOnboardingCard from './DashboardOnboardingCard.vue'

const { t } = useI18n()

import type { DataTableHeader } from '@/types/vuetify'

const props = withDefaults(
  defineProps<{
    activeOrganisationId?: number | null
    canAccessTenantAdmin?: boolean
    isOrganisationAdmin?: boolean
  }>(),
  {
    activeOrganisationId: null,
    canAccessTenantAdmin: false,
    isOrganisationAdmin: false,
  },
)

const canAccessOrganisationSettings = computed(
  () => props.canAccessTenantAdmin || props.isOrganisationAdmin,
)

const salesEventHeaders = computed((): DataTableHeader[] => [
  { title: t('dashboard.salesTable.event'), key: 'name' },
  { title: t('dashboard.salesTable.period'), key: 'period', sortable: false },
  { title: t('dashboard.salesTable.orders'), key: 'distinct_orders_count', align: 'end' },
  { title: t('dashboard.salesTable.lineItems'), key: 'line_cents', align: 'end' },
  { title: t('dashboard.salesTable.open'), key: 'open_cents', align: 'end' },
])

const orgIdRef = toRef(props, 'activeOrganisationId')
const { summary, loading, loadError, reload } = useDashboardSummary(orgIdRef)

const statusOrder = ['prod', 'test', 'config', 'archive'] as const

const eventsDetail = computed(() => {
  if (!summary.value) return ''
  return eventsStatDetail(summary.value.events_by_status, summary.value.running_events_count)
})

const hasSalesSection = computed(() => {
  if (!summary.value) return false
  return (summary.value.events_by_status?.prod || 0) > 0
})

function routeTo(name: string) {
  return { name }
}

function attentionClass(type: string) {
  if (type === 'missing_twint_qr') return 'warn'
  return 'info'
}

function attentionIcon(type: string) {
  if (type === 'missing_twint_qr') return 'mdi-alert'
  return 'mdi-information'
}
</script>

<style scoped>
.dashboard-header {
  margin-bottom: 1.5rem;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 2.2rem;
  color: rgb(var(--v-theme-on-surface));
  font-weight: 700;
}

.subtitle {
  margin: 0.5rem 0 0;
  opacity: 0.7;
  font-size: 1rem;
  font-weight: 500;
}

.empty-hint,
.muted {
  opacity: 0.7;
}

.toolbar {
  margin-bottom: 1rem;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 1rem;
  transition: transform 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
  border-radius: 0.85rem;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  margin: 0 0 0.5rem;
  opacity: 0.7;
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  margin: 0.5rem 0 0.25rem;
  font-size: 1.8rem;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.card-detail {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.7;
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.quick-link {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
}

.quick-link:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.content-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.section-card {
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 1rem;
  padding: 1.5rem;
}

.section-card h2 {
  margin: 0 0 1rem;
  color: rgb(var(--v-theme-on-surface));
  font-size: 1.2rem;
  font-weight: 700;
}

.subsection-title {
  margin: 1.25rem 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}

.status-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.running-hint {
  margin: 1rem 0 0;
  opacity: 0.7;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: background 0.2s ease;
}

.activity-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.activity-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.activity-badge.info {
  background: rgb(var(--v-theme-primary));
}

.activity-badge.info .activity-badge-icon {
  color: rgb(var(--v-theme-on-primary));
}

.activity-badge.warn {
  background: rgb(var(--v-theme-warning));
}

.activity-badge.warn .activity-badge-icon {
  color: rgb(var(--v-theme-on-warning));
}

.activity-text {
  flex: 1;
}

.activity-title {
  margin: 0;
  color: rgb(var(--v-theme-on-surface));
  font-weight: 600;
  font-size: 0.95rem;
}

.activity-time {
  margin: 0.25rem 0 0;
  opacity: 0.7;
  font-size: 0.85rem;
}

.sales-section {
  margin-bottom: 2rem;
}

.footnote {
  margin: 0 0 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.summary-card {
  padding: 0.75rem 1rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-label {
  font-size: 0.8rem;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.summary-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.small {
  font-size: 0.8rem;
}

@media (max-width: 992px) {
  .dashboard-header {
    margin-bottom: 1rem;
  }

  .dashboard-header h1 {
    font-size: 1.8rem;
  }

  .cards-grid {
    grid-template-columns: 1fr;
  }

  .content-section {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 1.25rem;
  }
}
</style>
