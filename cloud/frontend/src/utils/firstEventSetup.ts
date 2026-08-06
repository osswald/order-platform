import type { RouteLocationRaw } from 'vue-router'

export type FirstEventSetupStepId =
  | 'menu'
  | 'waiters'
  | 'event'
  | 'station'
  | 'layout'
  | 'done'

export const FIRST_EVENT_SETUP_STEPS: FirstEventSetupStepId[] = [
  'menu',
  'waiters',
  'event',
  'station',
  'layout',
  'done',
]

export interface FirstEventSetupState {
  available: boolean
  completed: boolean
  dismissed: boolean
  in_progress_event_id: number | null
}

export interface FirstEventSetupProgressInput {
  sellableArticleCount: number
  waiterCount: number
  inProgressEventId: number | null
  hasStationWithArticles: boolean
  hasEventWaiter: boolean
  hasAppLayout: boolean
}

export function firstEventSetupCtaVisible(state: FirstEventSetupState | null | undefined): boolean {
  return !!state?.available
}

export function firstEventSetupIsContinue(state: FirstEventSetupState | null | undefined): boolean {
  return firstEventSetupCtaVisible(state) && state?.in_progress_event_id != null
}

export function firstEventSetupWizardRoute(
  organisationId: number,
  step?: FirstEventSetupStepId,
): RouteLocationRaw {
  return {
    name: 'first-event-setup',
    query: {
      organisationId: String(organisationId),
      ...(step ? { step } : {}),
    },
  }
}

export function resolveFirstEventSetupStep(
  progress: FirstEventSetupProgressInput,
): FirstEventSetupStepId {
  if (progress.sellableArticleCount < 1) return 'menu'
  if (progress.waiterCount < 1) return 'waiters'
  if (progress.inProgressEventId == null) return 'event'
  if (!progress.hasStationWithArticles || !progress.hasEventWaiter) return 'station'
  if (!progress.hasAppLayout) return 'layout'
  return 'done'
}

export function suggestLayoutGrid(articleCount: number): { width: number; height: number } {
  const count = Math.max(1, articleCount)
  const width = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(count))))
  const height = Math.max(2, Math.ceil(count / width))
  return { width, height }
}

export function suggestLayoutCells(
  articles: Array<{ id: number; name: string; label?: string | null }>,
): Array<{ row: number; col: number; label: string; color: string; article_ids: number[] }> {
  const { width } = suggestLayoutGrid(articles.length)
  return articles.map((article, index) => ({
    row: Math.floor(index / width),
    col: index % width,
    label: (article.label || article.name || '').trim() || `Item ${index + 1}`,
    color: '#eeeeee',
    article_ids: [article.id],
  }))
}
