/** Build query path for event stats API. */
import { formatDateRange, formatTimeRange } from './localeFormat'

export type TimelineBucket = { start: string; end: string; label: string }

export function timelineBucketTooltipTitle(
  buckets: TimelineBucket[],
  dataIndex: number | undefined,
  locale: string,
): string {
  if (dataIndex == null || dataIndex < 0 || dataIndex >= buckets.length) return ''
  const bucket = buckets[dataIndex]
  const start = new Date(bucket.start)
  const end = new Date(bucket.end)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '—'
  const sameDay =
    start.getFullYear() === end.getFullYear() &&
    start.getMonth() === end.getMonth() &&
    start.getDate() === end.getDate()
  if (sameDay) {
    return formatTimeRange(bucket.start, bucket.end, locale)
  }
  return formatDateRange(bucket.start, bucket.end, locale)
}

export function buildEventStatsPath(
  eventId: number,
  from: Date,
  to: Date,
  articleIds: number[],
  categoryIds: number[] = [],
  bucketCount: number = 24,
): string {
  const params = new URLSearchParams()
  params.set('from', from.toISOString())
  params.set('to', to.toISOString())
  params.set('bucket_count', String(bucketCount))
  for (const id of articleIds) {
    params.append('article_ids', String(id))
  }
  for (const id of categoryIds) {
    params.append('category_ids', String(id))
  }
  return `/events/${eventId}/stats?${params.toString()}`
}

export function clampStatsRange(
  eventStart: Date,
  eventEnd: Date,
  now: Date = new Date(),
): { from: Date; to: Date } {
  const from = eventStart
  const endCap = eventEnd.getTime() < now.getTime() ? eventEnd : now
  const to = endCap.getTime() < from.getTime() ? from : endCap
  return { from, to }
}
