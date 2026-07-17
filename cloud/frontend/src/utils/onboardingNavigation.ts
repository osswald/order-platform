import type { RouteLocationRaw } from 'vue-router'
import type { OnboardingTask } from '@/types/ui'

export function onboardingTaskRoute(task: OnboardingTask): RouteLocationRaw | null {
  if (!task.target_route) return null
  return {
    name: task.target_route,
    params: task.target_params ?? undefined,
    query: task.target_query ?? undefined,
  }
}

export function visibleOnboardingTasks(
  tasks: OnboardingTask[],
  canAccessOrganisationSettings: boolean,
): OnboardingTask[] {
  return tasks.filter((task) => {
    if (!task.visible) return false
    if (task.group === 'organisation' && !canAccessOrganisationSettings) return false
    return true
  })
}

export function onboardingProgress(tasks: OnboardingTask[]): { done: number; total: number } {
  const total = tasks.length
  const done = tasks.filter((task) => task.done).length
  return { done, total }
}
