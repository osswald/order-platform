import { useDirtyAutosave } from './useDirtyAutosave'
import type { DirtyAutosaveHandle, DirtyAutosaveOptions } from './useDirtyAutosave'

/**
 * Debounced autosave for event configuration PUT payloads.
 * Wraps useDirtyAutosave with the event-configuration naming convention.
 */
export function useEventConfigurationAutosave(
  options: DirtyAutosaveOptions,
): DirtyAutosaveHandle {
  return useDirtyAutosave(options)
}
