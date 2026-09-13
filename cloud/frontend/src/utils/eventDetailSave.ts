/** Body for a status-only event update (partial EventUpdate). */
export function statusOnlyUpdatePayload(status: string): { status: string } {
  return { status }
}

/**
 * Update the status field inside a serialized stammdaten baseline without
 * touching other fields (so unrelated dirty edits stay dirty).
 */
export function stammdatenBaselineAfterStatusSave(
  baselineJson: string,
  newStatus: string,
): string {
  if (!baselineJson) return baselineJson
  try {
    const parsed = JSON.parse(baselineJson) as Record<string, unknown>
    return JSON.stringify({ ...parsed, status: newStatus })
  } catch {
    return baselineJson
  }
}

/** Body for a pickup-prefix-mode-only event update (partial EventUpdate). */
export function pickupPrefixModeOnlyUpdatePayload(
  mode: 'register' | 'station',
): { pickup_prefix_mode: 'register' | 'station' } {
  return { pickup_prefix_mode: mode === 'station' ? 'station' : 'register' }
}

/**
 * Update pickupPrefixMode inside a serialized stammdaten baseline without
 * touching other fields (so unrelated dirty edits stay dirty).
 */
export function stammdatenBaselineAfterPickupPrefixModeSave(
  baselineJson: string,
  mode: 'register' | 'station',
): string {
  if (!baselineJson) return baselineJson
  try {
    const parsed = JSON.parse(baselineJson) as Record<string, unknown>
    return JSON.stringify({
      ...parsed,
      pickupPrefixMode: mode === 'station' ? 'station' : 'register',
    })
  } catch {
    return baselineJson
  }
}

/**
 * Snapshot for event-configuration autosave, including pickup prefix mode
 * (stored on the event, but edited in the stations/registers UI).
 */
export function eventConfigurationAutosaveSnapshot(input: {
  pickupPrefixMode: 'register' | 'station'
  configuration: unknown
}): { pickupPrefixMode: 'register' | 'station'; configuration: unknown } {
  return {
    pickupPrefixMode: input.pickupPrefixMode === 'station' ? 'station' : 'register',
    configuration: input.configuration,
  }
}

export type EventStammdatenSaveNavigation =
  | { kind: 'stay' }
  | { kind: 'goToDetail'; id: number }

/**
 * After a successful stammdaten create/edit save, stay on the event detail
 * (create navigates to the new id).
 */
export function resolveEventStammdatenSaveNavigation(
  mode: 'create' | 'edit',
  createdId?: number | null,
): EventStammdatenSaveNavigation {
  if (mode === 'edit') return { kind: 'stay' }
  if (createdId == null || Number.isNaN(Number(createdId))) {
    throw new Error('createdId is required after create')
  }
  return { kind: 'goToDetail', id: Number(createdId) }
}
