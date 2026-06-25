import { describe, expect, it } from 'vitest'
import type { OnboardingTask } from '@/types/ui'
import {
  onboardingProgress,
  onboardingTaskRoute,
  visibleOnboardingTasks,
} from './onboardingNavigation'

function task(overrides: Partial<OnboardingTask> = {}): OnboardingTask {
  return {
    id: 'create_waiter',
    group: 'catalogue',
    done: false,
    visible: true,
    target_route: 'waiters-new',
    target_params: null,
    target_query: null,
    target_event_id: null,
    ...overrides,
  }
}

describe('onboardingNavigation', () => {
  it('builds router location from task target', () => {
    expect(
      onboardingTaskRoute(
        task({
          target_route: 'events-detail',
          target_params: { id: '5' },
          target_query: { section: 'kassen' },
        }),
      ),
    ).toEqual({
      name: 'events-detail',
      params: { id: '5' },
      query: { section: 'kassen' },
    })
  })

  it('filters organisation tasks without org settings access', () => {
    const tasks = [
      task({ id: 'configure_vat', group: 'organisation' }),
      task({ id: 'create_waiter', group: 'catalogue' }),
    ]
    expect(visibleOnboardingTasks(tasks, false).map((row) => row.id)).toEqual(['create_waiter'])
    expect(visibleOnboardingTasks(tasks, true).map((row) => row.id)).toEqual([
      'configure_vat',
      'create_waiter',
    ])
  })

  it('counts onboarding progress', () => {
    expect(
      onboardingProgress([
        task({ done: true }),
        task({ id: 'create_article', done: false }),
      ]),
    ).toEqual({ done: 1, total: 2 })
  })
})
