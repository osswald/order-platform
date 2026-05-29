<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>Dashboard</h1>
      <p v-if="summary" class="subtitle">Übersicht für {{ summary.organisation_name }}</p>
      <p v-else class="subtitle">Willkommen bei Vendiqo</p>
    </div>

    <p v-if="activeOrganisationId == null" class="empty-hint">
      Bitte wählen Sie links eine Organisation.
    </p>

    <p v-else-if="loadError" class="error">{{ loadError }}</p>

    <p v-else-if="loading" class="muted">Laden…</p>

    <template v-else-if="summary">
      <div class="toolbar">
        <Button
          label="Aktualisieren"
          type="button"
          class="secondary-button"
          icon="pi pi-refresh"
          :disabled="loading"
          @click="reload"
        />
      </div>

      <div class="cards-grid">
        <div class="stat-card">
          <div class="card-icon"><i class="pi pi-calendar" aria-hidden="true"></i></div>
          <div class="card-content">
            <h3>Veranstaltungen</h3>
            <p class="card-value">{{ summary.events_total }}</p>
            <p class="card-detail">{{ eventsDetail }}</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><i class="pi pi-id-card" aria-hidden="true"></i></div>
          <div class="card-content">
            <h3>Kellner</h3>
            <p class="card-value">{{ summary.catalog.waiters }}</p>
            <p class="card-detail">Für diese Organisation</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><i class="pi pi-tags" aria-hidden="true"></i></div>
          <div class="card-content">
            <h3>Artikel</h3>
            <p class="card-value">{{ summary.catalog.articles }}</p>
            <p class="card-detail">{{ summary.catalog.categories }} Kategorien</p>
          </div>
        </div>

        <div class="stat-card">
          <div class="card-icon"><i class="pi pi-calendar-plus" aria-hidden="true"></i></div>
          <div class="card-content">
            <h3>Geräteausleihen</h3>
            <p class="card-value">{{ summary.lendings.current }}</p>
            <p class="card-detail">{{ summary.lendings.planned }} geplant</p>
          </div>
        </div>
      </div>

      <div class="quick-links">
        <RouterLink :to="routeTo('events')" class="quick-link">Veranstaltungen</RouterLink>
        <RouterLink :to="routeTo('waiters')" class="quick-link">Kellner</RouterLink>
        <RouterLink :to="routeTo('articles')" class="quick-link">Artikel</RouterLink>
        <RouterLink :to="routeTo('appliance-lendings')" class="quick-link">Geräteausleihen</RouterLink>
      </div>

      <div class="content-section">
        <div class="section-card">
          <h2>Veranstaltungen nach Status</h2>
          <div class="status-chips">
            <Tag
              v-for="status in statusOrder"
              :key="status"
              :value="`${statusLabel(status)}: ${summary.events_by_status[status] || 0}`"
              :severity="statusSeverity(status)"
            />
          </div>
          <p v-if="summary.running_events_count > 0" class="running-hint">
            <i class="pi pi-play-circle" aria-hidden="true"></i>
            {{ summary.running_events_count }} Veranstaltung(en) laufen gerade (Test oder Produktiv).
          </p>
        </div>

        <div class="section-card">
          <h2>Aufmerksamkeit</h2>
          <div v-if="summary.attention.length" class="activity-list">
            <RouterLink
              v-for="(item, idx) in summary.attention"
              :key="`${item.type}-${item.event_id}-${idx}`"
              :to="routeTo('events')"
              class="activity-item"
            >
              <span class="activity-badge" :class="attentionClass(item.type)">
                <i :class="attentionIcon(item.type)" aria-hidden="true"></i>
              </span>
              <div class="activity-text">
                <p class="activity-title">{{ item.message }}</p>
                <p class="activity-time">{{ item.event_name }}</p>
              </div>
            </RouterLink>
          </div>
          <p v-else class="muted">Alles bereit — keine offenen Hinweise.</p>
        </div>
      </div>

      <div v-if="hasSalesSection" class="section-card sales-section">
        <h2>Umsatz (Produktivbetrieb)</h2>
        <p class="muted small footnote">
          Aggregiert aus Pi-synchronisierten Bestellungen. Nur Veranstaltungen im Status Produktivbetrieb.
        </p>

        <div class="summary-grid">
          <div class="summary-card">
            <span class="summary-label">Bestellungen</span>
            <span class="summary-value">{{ summary.sales.totals.distinct_orders_count }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Positionen</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.line_cents) }} {{ summary.sales.currency }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Bezahlt</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.paid_cents) }} {{ summary.sales.currency }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Offen</span>
            <span class="summary-value">{{ formatAmount(summary.sales.totals.open_cents) }} {{ summary.sales.currency }}</span>
          </div>
        </div>

        <h3 class="subsection-title">Veranstaltungen mit Umsatz</h3>
        <p v-if="!summary.sales.by_event.length" class="muted">Noch keine Produktiv-Veranstaltungen oder keine synchronisierten Bestellungen.</p>
        <DataTable
          v-else
          :value="summary.sales.by_event"
          dataKey="event_id"
          class="list-table"
          responsiveLayout="stack"
          breakpoint="768px"
        >
          <Column field="name" header="Veranstaltung" />
          <Column header="Zeitraum">
            <template #body="{ data }">{{ formatEventDateRange(data.start, data.end) }}</template>
          </Column>
          <Column header="Bestellungen" style="text-align: right">
            <template #body="{ data }">{{ data.distinct_orders_count }}</template>
          </Column>
          <Column header="Positionen" style="text-align: right">
            <template #body="{ data }">{{ formatAmount(data.line_cents) }}</template>
          </Column>
          <Column header="Offen" style="text-align: right">
            <template #body="{ data }">{{ formatAmount(data.open_cents) }}</template>
          </Column>
        </DataTable>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { useDashboardSummary } from '../composables/useDashboardSummary'
import { eventsStatDetail, formatEventDateRange, statusLabel } from '../utils/dashboardMetrics'
import { formatAmount } from '../utils/money'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const orgIdRef = toRef(props, 'activeOrganisationId')
const { summary, loading, loadError, reload } = useDashboardSummary(orgIdRef)

const statusOrder = ['prod', 'test', 'config', 'archive']

const eventsDetail = computed(() => {
  if (!summary.value) return ''
  return eventsStatDetail(summary.value.events_by_status, summary.value.running_events_count)
})

const hasSalesSection = computed(() => {
  if (!summary.value) return false
  return (summary.value.events_by_status?.prod || 0) > 0
})

function routeTo(name) {
  const query = {}
  if (props.activeOrganisationId != null) {
    query.organisation = String(props.activeOrganisationId)
  }
  return { name, query }
}

function statusSeverity(status) {
  const map = { prod: 'success', test: 'warn', config: 'info', archive: 'secondary' }
  return map[status] || 'secondary'
}

function attentionClass(type) {
  if (type === 'missing_twint_qr') return 'warn'
  return 'info'
}

function attentionIcon(type) {
  if (type === 'missing_twint_qr') return 'pi pi-exclamation-triangle'
  return 'pi pi-info-circle'
}
</script>

<style scoped>
.dashboard {
  padding: 2rem;
  background: var(--p-surface-ground);
  min-height: 100%;
}

.dashboard-header {
  margin-bottom: 1.5rem;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 2.2rem;
  color: var(--p-text-color);
  font-weight: 700;
}

.subtitle {
  margin: 0.5rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 1rem;
  font-weight: 500;
}

.empty-hint,
.muted {
  color: var(--p-text-muted-color);
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
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  box-shadow: var(--p-card-shadow);
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
  background: var(--p-primary-50);
  color: var(--p-primary-color);
  border-radius: 0.85rem;
  font-size: 1.35rem;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  margin: 0 0 0.5rem;
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.8;
}

.card-value {
  margin: 0.5rem 0 0.25rem;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.card-detail {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.quick-link {
  padding: 0.5rem 1rem;
  border-radius: var(--p-border-radius-md);
  border: 1px solid var(--p-content-border-color);
  background: var(--p-surface-card);
  color: var(--p-primary-color);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
}

.quick-link:hover {
  background: var(--p-surface-hover);
}

.content-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.section-card {
  background: var(--p-surface-card);
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: var(--p-card-shadow);
}

.section-card h2 {
  margin: 0 0 1rem;
  color: var(--p-text-color);
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
  color: var(--p-text-muted-color);
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
  background: var(--p-surface-50);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  text-decoration: none;
  color: inherit;
  transition: background 0.2s ease;
}

.activity-item:hover {
  background: var(--p-surface-hover);
}

.activity-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  flex-shrink: 0;
  color: #fff;
}

.activity-badge.info {
  background: var(--p-primary-color);
}

.activity-badge.warn {
  background: var(--p-orange-500);
}

.activity-text {
  flex: 1;
}

.activity-title {
  margin: 0;
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 0.95rem;
}

.activity-time {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
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
  background: var(--p-surface-50);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-label {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.summary-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--p-text-color);
}

@media (max-width: 768px) {
  .dashboard {
    padding: 1rem;
  }

  .dashboard-header {
    margin-bottom: 1rem;
  }

  .dashboard-header h1 {
    font-size: 1.8rem;
  }

  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .toolbar :deep(.p-button) {
    width: 100%;
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
