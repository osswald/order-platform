import { useDirtyAutosave } from './useDirtyAutosave'

/**
 * Debounced autosave for event configuration PUT payloads.
 * Wraps useDirtyAutosave with the event-configuration naming convention.
 */
export function useEventConfigurationAutosave({
  getSnapshot,
  saveFn,
  watchSource,
  enabled,
  validate,
  debounceMs,
}) {
  return useDirtyAutosave({
    getSnapshot,
    saveFn,
    watchSource,
    enabled,
    validate,
    debounceMs,
  })
}
