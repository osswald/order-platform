<template>
  <div class="event-stats-page vq-page">
    <div class="page-header">
      <div>
        <v-btn prepend-icon="mdi-arrow-left" type="button" @click="goBack">
          {{ t('events.stats.back') }}
        </v-btn>
        <h1>{{ t('events.stats.title') }}</h1>
        <p v-if="event" class="subtitle">{{ event.name }}</p>
      </div>
    </div>

    <p v-if="activeOrganisationId == null" class="empty-hint">{{ t('common.noOrganisation') }}</p>
    <p v-else-if="eventLoadError" class="error">{{ eventLoadError }}</p>
    <p v-else-if="eventLoading" class="muted">{{ t('common.loading') }}</p>

    <template v-else-if="event">
      <section class="filters-section">
        <h2 class="section-title">{{ t('events.stats.filters') }}</h2>
        <div class="filters-row">
          <v-text-field
            :model-value="formatLocalDatetime(filterFrom)"
            type="datetime-local"
            :label="t('events.stats.from')"
            density="compact"
            hide-details
            class="filter-field"
            @update:model-value="filterFrom = parseLocalDatetime($event)"
          />
          <v-text-field
            :model-value="formatLocalDatetime(filterTo)"
            type="datetime-local"
            :label="t('events.stats.to')"
            density="compact"
            hide-details
            class="filter-field"
            @update:model-value="filterTo = parseLocalDatetime($event)"
          />
        </div>
        <div class="preset-row">
          <v-btn
            v-for="preset in presets"
            :key="preset.id"
            variant="outlined"
            size="small"
            type="button"
            @click="applyPreset(preset.id)"
          >
            {{ preset.label }}
          </v-btn>
        </div>
        <v-autocomplete
          v-model="selectedArticleIds"
          :items="articleOptions"
          item-title="label"
          item-value="value"
          :label="t('events.stats.articles')"
          multiple
          chips
          closable-chips
          density="compact"
          hide-details
          class="article-select"
        />
        <v-autocomplete
          v-model="selectedCategoryIds"
          :items="categoryOptions"
          item-title="label"
          item-value="value"
          :label="t('events.stats.categories')"
          multiple
          chips
          closable-chips
          density="compact"
          hide-details
          class="article-select"
        />
        <div class="bucket-count-row">
          <span class="bucket-count-label">{{ t('events.stats.bucketCount') }}</span>
          <v-btn-toggle v-model="bucketCount" density="compact" mandatory>
            <v-btn :value="12" size="small">12</v-btn>
            <v-btn :value="24" size="small">24</v-btn>
            <v-btn :value="48" size="small">48</v-btn>
          </v-btn-toggle>
        </div>
        <div class="filters-actions">
          <v-btn color="primary" type="button" :disabled="statsLoading || !canApply" @click="loadStats">
            {{ t('events.stats.apply') }}
          </v-btn>
          <v-btn variant="outlined" type="button" :disabled="statsLoading" @click="loadStats">
            {{ t('common.refresh') }}
          </v-btn>
        </div>
      </section>

      <p v-if="statsError" class="error">{{ statsError }}</p>
      <p v-else-if="statsLoading" class="muted">{{ t('common.loading') }}</p>

      <template v-else-if="stats">
        <div class="summary-grid">
          <div class="summary-card">
            <span class="summary-label">{{ t('events.stats.orderCount') }}</span>
            <span class="summary-value">{{ stats.totals.distinct_orders_count }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ t('events.tabs.lineValue') }}</span>
            <span class="summary-value">{{ formatMoney(stats.totals.line_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ t('events.tabs.paid') }}</span>
            <span class="summary-value">{{ formatMoney(stats.totals.paid_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ t('events.stats.averageOrderValue') }}</span>
            <span class="summary-value">{{ formatMoney(stats.totals.average_order_value_cents) }}</span>
          </div>
        </div>

        <section class="chart-section">
          <h2 class="section-title">{{ t('events.stats.revenueTimeline') }}</h2>
          <div v-if="revenueChartData" class="chart-container">
            <Line :data="revenueChartData" :options="revenueChartOptions" />
          </div>
          <p v-else class="muted">{{ t('events.stats.noData') }}</p>
        </section>

        <section class="chart-section">
          <div class="chart-header">
            <h2 class="section-title">{{ t('events.stats.topArticles') }}</h2>
            <v-btn-toggle v-model="topArticlesMetric" density="compact" mandatory>
              <v-btn value="qty" size="small">{{ t('events.stats.qty') }}</v-btn>
              <v-btn value="revenue" size="small">{{ t('events.tabs.lineValue') }}</v-btn>
            </v-btn-toggle>
          </div>
          <div v-if="topArticlesChartData" class="chart-container">
            <Bar :data="topArticlesChartData" :options="topArticlesChartOptions" />
          </div>
          <p v-else class="muted">{{ t('events.stats.noData') }}</p>
        </section>

        <section class="chart-section">
          <div class="chart-header">
            <h2 class="section-title">{{ t('events.stats.articleTimeline') }}</h2>
            <v-btn-toggle v-model="articleChartType" density="compact" mandatory>
              <v-btn value="line" size="small">{{ t('events.stats.chartLine') }}</v-btn>
              <v-btn value="bar" size="small">{{ t('events.stats.chartBar') }}</v-btn>
            </v-btn-toggle>
          </div>
          <p v-if="!selectedArticleIds.length" class="muted empty-chart-hint">
            {{ t('events.stats.selectArticlesHint') }}
          </p>
          <div v-else-if="articleChartData" class="chart-container">
            <Line v-if="articleChartType === 'line'" :data="articleChartData" :options="articleLineChartOptions" />
            <Bar v-else :data="articleChartData" :options="articleBarChartOptions" />
          </div>
        </section>

        <section class="chart-section">
          <div class="chart-header">
            <h2 class="section-title">{{ t('events.stats.categoryTimeline') }}</h2>
            <v-btn-toggle v-model="categoryChartType" density="compact" mandatory>
              <v-btn value="line" size="small">{{ t('events.stats.chartLine') }}</v-btn>
              <v-btn value="bar" size="small">{{ t('events.stats.chartBar') }}</v-btn>
            </v-btn-toggle>
          </div>
          <p v-if="!selectedCategoryIds.length" class="muted empty-chart-hint">
            {{ t('events.stats.selectCategoriesHint') }}
          </p>
          <div v-else-if="categoryChartData" class="chart-container">
            <Line v-if="categoryChartType === 'line'" :data="categoryChartData" :options="categoryLineChartOptions" />
            <Bar v-else :data="categoryChartData" :options="categoryBarChartOptions" />
          </div>
        </section>

        <div class="charts-grid">
          <section class="chart-section">
            <h2 class="section-title">{{ t('events.tabs.salesByPayment') }}</h2>
            <div v-if="paymentChartData" class="chart-container chart-container--pie">
              <Pie :data="paymentChartData" :options="pieChartOptions" />
            </div>
            <p v-else class="muted">{{ t('events.stats.noData') }}</p>
          </section>

          <section class="chart-section">
            <h2 class="section-title">{{ t('events.stats.orderSource') }}</h2>
            <div v-if="orderSourceChartData" class="chart-container">
              <Bar :data="orderSourceChartData" :options="breakdownBarOptions" />
            </div>
            <p v-else class="muted">{{ t('events.stats.noData') }}</p>
          </section>

          <section class="chart-section">
            <h2 class="section-title">{{ t('events.tabs.salesByWaiter') }}</h2>
            <div v-if="waiterChartData" class="chart-container">
              <Bar :data="waiterChartData" :options="breakdownBarOptions" />
            </div>
            <p v-else class="muted">{{ t('events.stats.noData') }}</p>
          </section>

          <section class="chart-section">
            <h2 class="section-title">{{ t('events.tabs.salesByStation') }}</h2>
            <div v-if="stationChartData" class="chart-container">
              <Bar :data="stationChartData" :options="breakdownBarOptions" />
            </div>
            <p v-else class="muted">{{ t('events.stats.noData') }}</p>
          </section>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
  type TooltipItem,
  type ChartOptions,
} from 'chart.js'
import { Bar, Line, Pie } from 'vue-chartjs'
import { apiJson } from '../api'
import { formatMoney as formatMoneyWithCurrency } from '../utils/money'
import { buildEventStatsPath, clampStatsRange, timelineBucketTooltipTitle } from '../utils/eventStats'
import type { ArticleRead, EventConfigurationRead, EventRead, EventStatsRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  ArcElement,
)

const CHART_COLORS = [
  'rgb(25, 118, 210)',
  'rgb(56, 142, 60)',
  'rgb(251, 140, 0)',
  'rgb(211, 47, 47)',
  'rgb(123, 31, 162)',
  'rgb(0, 151, 167)',
]

const props = defineProps<{
  activeOrganisationId?: number | null
}>()

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const eventId = computed(() => Number(route.params.id))
const event = ref<EventRead | null>(null)
const eventLoading = ref(true)
const eventLoadError = ref('')
const config = ref<EventConfigurationRead | null>(null)
const articlesById = ref<Map<number, string>>(new Map())
const articleCategoryByArticleId = ref<Map<number, number>>(new Map())
const categoriesById = ref<Map<number, string>>(new Map())
const stats = ref<EventStatsRead | null>(null)
const statsLoading = ref(false)
const statsError = ref('')
const filterFrom = ref<Date | null>(null)
const filterTo = ref<Date | null>(null)
const selectedArticleIds = ref<number[]>([])
const selectedCategoryIds = ref<number[]>([])
const bucketCount = ref<12 | 24 | 48>(24)
const articleChartType = ref<'line' | 'bar'>('line')
const categoryChartType = ref<'line' | 'bar'>('line')
const topArticlesMetric = ref<'qty' | 'revenue'>('qty')

const presets = computed(() => [
  { id: 'full', label: t('events.stats.presetFull') },
  { id: 'today', label: t('events.stats.presetToday') },
  { id: 'last24h', label: t('events.stats.presetLast24h') },
])

const articleOptions = computed(() => {
  const stations = config.value?.stations ?? []
  const ids = new Set<number>()
  const options: { value: number; label: string }[] = []
  for (const station of stations) {
    for (const id of station.article_ids ?? []) {
      if (ids.has(id)) continue
      ids.add(id)
      options.push({ value: id, label: articlesById.value.get(id) ?? `#${id}` })
    }
  }
  return options.sort((a, b) => a.label.localeCompare(b.label))
})

const categoryOptions = computed(() => {
  const eventArticleIds = new Set(articleOptions.value.map((option) => option.value))
  const categoryIds = new Set<number>()
  for (const [articleId, categoryId] of articleCategoryByArticleId.value) {
    if (eventArticleIds.has(articleId)) {
      categoryIds.add(categoryId)
    }
  }
  return [...categoryIds]
    .map((id) => ({
      value: id,
      label: categoriesById.value.get(id) ?? `#${id}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

const canApply = computed(() => filterFrom.value != null && filterTo.value != null)

function buildTimelineChartOptions(buckets: { start: string; end: string; label: string }[]) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true },
      tooltip: {
        callbacks: {
          title(items: { dataIndex?: number }[]) {
            return timelineBucketTooltipTitle(buckets, items[0]?.dataIndex, locale.value)
          },
          label(context: TooltipItem<'line' | 'bar'>) {
            const qty = context.parsed.y ?? 0
            return `${context.dataset.label}: ${qty}`
          },
        },
      },
    },
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0 } },
    },
  }
}

function buildRevenueTimelineChartOptions(buckets: { start: string; end: string; label: string }[]) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title(items: { dataIndex?: number }[]) {
            return timelineBucketTooltipTitle(buckets, items[0]?.dataIndex, locale.value)
          },
          label(context: TooltipItem<'line'>) {
            const cents = Math.round((context.parsed.y ?? 0) * 100)
            return formatMoney(cents)
          },
        },
      },
    },
    scales: {
      y: { beginAtZero: true },
    },
  }
}

const articleLineChartOptions = computed(
  () => buildTimelineChartOptions(stats.value?.article_timeline?.buckets ?? []) as ChartOptions<'line'>,
)
const articleBarChartOptions = computed(
  () => buildTimelineChartOptions(stats.value?.article_timeline?.buckets ?? []) as ChartOptions<'bar'>,
)
const categoryLineChartOptions = computed(
  () => buildTimelineChartOptions(stats.value?.category_timeline?.buckets ?? []) as ChartOptions<'line'>,
)
const categoryBarChartOptions = computed(
  () => buildTimelineChartOptions(stats.value?.category_timeline?.buckets ?? []) as ChartOptions<'bar'>,
)
const revenueChartOptions = computed(
  () =>
    buildRevenueTimelineChartOptions(stats.value?.revenue_timeline?.buckets ?? []) as ChartOptions<'line'>,
)

const pieChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
}

const breakdownBarOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: {
    legend: { display: true },
    tooltip: {
      callbacks: {
        label(context: TooltipItem<'bar'>) {
          const label = context.dataset.label ?? ''
          const value = context.parsed.x ?? 0
          if (context.dataset.xAxisID === 'x-qty') {
            return `${label}: ${value}`
          }
          return `${label}: ${formatMoneyWithCurrency(Math.round(value * 100), statsCurrency.value, statsCountryCode.value)}`
        },
      },
    },
  },
  scales: {
    x: {
      type: 'linear' as const,
      position: 'bottom' as const,
      beginAtZero: true,
      title: { display: true, text: t('events.tabs.lineValue') },
    },
    'x-qty': {
      type: 'linear' as const,
      position: 'top' as const,
      beginAtZero: true,
      grid: { drawOnChartArea: false },
      title: { display: true, text: t('events.stats.qty') },
    },
  },
}))

const articleChartData = computed(() => {
  const timeline = stats.value?.article_timeline
  if (!timeline?.series?.length) return null
  return {
    labels: timeline.buckets.map((b) => b.label),
    datasets: timeline.series.map((series, index) => ({
      label: series.name,
      data: series.qty,
      borderColor: CHART_COLORS[index % CHART_COLORS.length],
      backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
      tension: 0.2,
    })),
  }
})

const categoryChartData = computed(() => {
  const timeline = stats.value?.category_timeline
  if (!timeline?.series?.length) return null
  return {
    labels: timeline.buckets.map((b) => b.label),
    datasets: timeline.series.map((series, index) => ({
      label: series.name,
      data: series.qty,
      borderColor: CHART_COLORS[index % CHART_COLORS.length],
      backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
      tension: 0.2,
    })),
  }
})

const revenueChartData = computed(() => {
  const timeline = stats.value?.revenue_timeline
  if (!timeline?.line_cents?.length) return null
  if (timeline.line_cents.every((value) => value === 0)) return null
  return {
    labels: timeline.buckets.map((b) => b.label),
    datasets: [
      {
        label: t('events.tabs.lineValue'),
        data: timeline.line_cents.map((cents) => cents / 100),
        borderColor: CHART_COLORS[0],
        backgroundColor: CHART_COLORS[0],
        tension: 0.2,
      },
    ],
  }
})

const topArticlesChartData = computed(() => {
  const rows = stats.value?.top_articles ?? []
  if (!rows.length) return null
  const sorted = [...rows].sort((a, b) =>
    topArticlesMetric.value === 'qty' ? b.qty - a.qty : b.line_cents - a.line_cents,
  )
  return {
    labels: sorted.map((row) => row.name),
    datasets: [
      {
        label: topArticlesMetric.value === 'qty' ? t('events.stats.qty') : t('events.tabs.lineValue'),
        data: sorted.map((row) =>
          topArticlesMetric.value === 'qty' ? row.qty : row.line_cents / 100,
        ),
        backgroundColor: CHART_COLORS[0],
      },
    ],
  }
})

const topArticlesChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label(context: TooltipItem<'bar'>) {
          const row = [...(stats.value?.top_articles ?? [])].sort((a, b) =>
            topArticlesMetric.value === 'qty' ? b.qty - a.qty : b.line_cents - a.line_cents,
          )[context.dataIndex]
          if (!row) return ''
          if (topArticlesMetric.value === 'qty') {
            return `${t('events.stats.qty')}: ${row.qty}`
          }
          return `${t('events.tabs.lineValue')}: ${formatMoneyWithCurrency(Math.round((context.parsed.x ?? 0) * 100), statsCurrency.value, statsCountryCode.value)}`
        },
      },
    },
  },
  scales: {
    x: { beginAtZero: true },
  },
}))

const paymentChartData = computed(() => {
  const rows = stats.value?.by_payment_type ?? []
  if (!rows.length) return null
  return {
    labels: rows.map((r) => r.label),
    datasets: [
      {
        data: rows.map((r) => r.amount_cents / 100),
        backgroundColor: rows.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
      },
    ],
  }
})

const orderSourceChartData = computed(() => {
  const rows = stats.value?.by_order_source ?? []
  if (!rows.length) return null
  return {
    labels: rows.map((row) => orderSourceLabel(row.source, row.label)),
    datasets: [
      {
        label: t('events.tabs.lineValue'),
        data: rows.map((row) => row.line_cents / 100),
        backgroundColor: CHART_COLORS[0],
        xAxisID: 'x',
      },
      {
        label: t('events.stats.qty'),
        data: rows.map((row) => row.qty),
        backgroundColor: CHART_COLORS[1],
        xAxisID: 'x-qty',
      },
    ],
  }
})

const waiterChartData = computed(() => {
  const rows = stats.value?.by_waiter ?? []
  if (!rows.length) return null
  return {
    labels: rows.map((r) => r.name),
    datasets: [
      {
        label: t('events.tabs.lineValue'),
        data: rows.map((r) => r.line_cents / 100),
        backgroundColor: CHART_COLORS[0],
        xAxisID: 'x',
      },
      {
        label: t('events.stats.qty'),
        data: rows.map((r) => r.qty),
        backgroundColor: CHART_COLORS[1],
        xAxisID: 'x-qty',
      },
    ],
  }
})

const stationChartData = computed(() => {
  const rows = stats.value?.by_station ?? []
  if (!rows.length) return null
  return {
    labels: rows.map((r) => r.name),
    datasets: [
      {
        label: t('events.tabs.lineValue'),
        data: rows.map((r) => r.line_cents / 100),
        backgroundColor: CHART_COLORS[0],
        xAxisID: 'x',
      },
      {
        label: t('events.stats.qty'),
        data: rows.map((r) => r.qty),
        backgroundColor: CHART_COLORS[1],
        xAxisID: 'x-qty',
      },
    ],
  }
})

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

function formatLocalDatetime(value: Date | null | undefined): string {
  if (!value || !(value instanceof Date) || Number.isNaN(value.getTime())) return ''
  return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())}T${pad2(value.getHours())}:${pad2(value.getMinutes())}`
}

function parseLocalDatetime(value: string | null | undefined): Date | null {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const statsCurrency = computed(
  () => stats.value?.currency || event.value?.organisation_currency || 'CHF',
)
const statsCountryCode = computed(
  () => stats.value?.country_code || event.value?.organisation_country_code || 'CH',
)

function formatMoney(cents: number): string {
  return formatMoneyWithCurrency(cents, statsCurrency.value, statsCountryCode.value)
}

function orderSourceLabel(source: string, fallback: string): string {
  if (source === 'waiter') return t('events.stats.orderSourceWaiter')
  if (source === 'cash_register') return t('events.stats.orderSourceCashRegister')
  return fallback
}

function goBack() {
  router.push({ name: 'events-detail', params: { id: String(eventId.value) } })
}

function initDefaultRange() {
  if (!event.value) return
  const start = new Date(event.value.start)
  const end = new Date(event.value.end)
  const range = clampStatsRange(start, end)
  filterFrom.value = range.from
  filterTo.value = range.to
}

function applyPreset(id: string) {
  if (!event.value) return
  const eventStart = new Date(event.value.start)
  const eventEnd = new Date(event.value.end)
  const now = new Date()

  if (id === 'full') {
    const range = clampStatsRange(eventStart, eventEnd, now)
    filterFrom.value = range.from
    filterTo.value = range.to
    return
  }
  if (id === 'today') {
    const start = new Date(now)
    start.setHours(0, 0, 0, 0)
    const end = new Date(now)
    end.setHours(23, 59, 59, 999)
    filterFrom.value = start
    filterTo.value = end
    return
  }
  if (id === 'last24h') {
    filterTo.value = now
    filterFrom.value = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  }
}

async function loadEvent() {
  eventLoading.value = true
  eventLoadError.value = ''
  try {
    event.value = await apiJson<EventRead>(`/events/${eventId.value}`)
    initDefaultRange()
  } catch (e: unknown) {
    event.value = null
    eventLoadError.value = getErrorMessage(e, t('events.messages.notFound'))
  } finally {
    eventLoading.value = false
  }
}

async function loadArticles() {
  try {
    const articles = await apiJson<ArticleRead[]>('/articles/')
    const nameMap = new Map<number, string>()
    const categoryByArticle = new Map<number, number>()
    const categoryNameMap = new Map<number, string>()
    for (const article of articles) {
      nameMap.set(article.id, article.name)
      categoryByArticle.set(article.id, article.article_category_id)
      categoryNameMap.set(article.article_category_id, article.article_category_name)
    }
    articlesById.value = nameMap
    articleCategoryByArticleId.value = categoryByArticle
    categoriesById.value = categoryNameMap
  } catch {
    articlesById.value = new Map()
    articleCategoryByArticleId.value = new Map()
    categoriesById.value = new Map()
  }
}

async function loadConfiguration() {
  try {
    config.value = await apiJson<EventConfigurationRead>(
      `/events/${eventId.value}/configuration?fields=summary`,
    )
  } catch {
    config.value = null
  }
}

async function loadStats() {
  if (!canApply.value || filterFrom.value == null || filterTo.value == null) return
  statsLoading.value = true
  statsError.value = ''
  try {
    const path = buildEventStatsPath(
      eventId.value,
      filterFrom.value,
      filterTo.value,
      selectedArticleIds.value,
      selectedCategoryIds.value,
      bucketCount.value,
    )
    stats.value = await apiJson<EventStatsRead>(path)
  } catch (e: unknown) {
    stats.value = null
    statsError.value = getErrorMessage(e, t('events.stats.loadFailed'))
  } finally {
    statsLoading.value = false
  }
}

onMounted(async () => {
  if (props.activeOrganisationId == null) {
    eventLoading.value = false
    return
  }
  await loadEvent()
  await loadConfiguration()
  await loadArticles()
  if (event.value) {
    await loadStats()
  }
})

watch(
  () => route.params.id,
  async () => {
    if (props.activeOrganisationId == null) return
    await loadEvent()
    await loadConfiguration()
    await loadArticles()
    if (event.value) {
      await loadStats()
    }
  },
)
</script>

<style scoped>
.page-header {
  margin-bottom: 1.5rem;
}

.subtitle {
  margin: 0.25rem 0 0;
  opacity: 0.75;
}

.filters-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.section-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.filter-field {
  min-width: 14rem;
  flex: 1;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.article-select {
  margin-bottom: 0.75rem;
}

.bucket-count-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.bucket-count-label {
  font-size: 0.9rem;
  opacity: 0.85;
}

.filters-actions {
  display: flex;
  gap: 0.75rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.summary-label {
  font-size: 0.85rem;
  opacity: 0.75;
}

.summary-value {
  font-size: 1.35rem;
  font-weight: 600;
}

.chart-section {
  margin-bottom: 1.5rem;
}

.chart-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.chart-container {
  height: 18rem;
}

.chart-container--pie {
  height: 16rem;
  max-width: 20rem;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1rem;
}

.empty-chart-hint {
  padding: 1rem 0;
}
</style>
