import { ref, computed, watch, onBeforeUnmount } from 'vue'
import type { ComputedRef, Ref, WatchSource } from 'vue'
import type { SaveStatus } from '@/types/ui'

const DEBOUNCE_MS = 800

function serializeSnapshot(getSnapshot: () => unknown): string {
  try {
    return JSON.stringify(getSnapshot())
  } catch {
    return ''
  }
}

type EnabledSource = boolean | Ref<boolean> | ComputedRef<boolean> | (() => boolean)

export interface DirtyAutosaveOptions {
  getSnapshot: () => unknown
  saveFn: () => Promise<boolean>
  watchSource?: WatchSource<unknown> | null
  enabled?: EnabledSource
  debounceMs?: number
  validate?: (() => string | null | undefined) | null
}

export interface DirtyAutosaveHandle {
  status: Ref<SaveStatus>
  errorMessage: Ref<string>
  isDirty: ComputedRef<boolean>
  markSaved: () => void
  resetSnapshot: () => void
  flush: () => Promise<boolean>
  scheduleSave: () => void
  runSave: () => Promise<boolean>
  setError: (msg: string) => void
}

/**
 * Tracks dirty state and debounced auto-save for a single editable silo.
 */
export function useDirtyAutosave({
  getSnapshot,
  saveFn,
  watchSource = null,
  enabled = true,
  debounceMs = DEBOUNCE_MS,
  validate = null,
}: DirtyAutosaveOptions): DirtyAutosaveHandle {
  const savedSnapshot = ref('')
  const status = ref<SaveStatus>('idle')
  const errorMessage = ref('')
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let saveInFlight = false
  let pendingAfterSave = false

  const isEnabled = (): boolean => {
    if (typeof enabled === 'function') return enabled()
    if (enabled && typeof enabled === 'object' && 'value' in enabled) return !!enabled.value
    return enabled !== false
  }

  const isDirty = computed(() => {
    if (!savedSnapshot.value) return false
    return serializeSnapshot(getSnapshot) !== savedSnapshot.value
  })

  function validationMessage(): string | null {
    if (!validate) return null
    const msg = validate()
    return msg && String(msg).trim() ? String(msg).trim() : null
  }

  function markSaved() {
    savedSnapshot.value = serializeSnapshot(getSnapshot)
    status.value = 'saved'
    errorMessage.value = ''
  }

  function resetSnapshot() {
    savedSnapshot.value = ''
    status.value = 'idle'
    errorMessage.value = ''
  }

  function clearDebounce() {
    if (debounceTimer != null) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  async function runSave(): Promise<boolean> {
    if (!isEnabled() || !isDirty.value) return true
    const validationErr = validationMessage()
    if (validationErr) {
      status.value = 'dirty'
      errorMessage.value = validationErr
      return false
    }
    if (saveInFlight) {
      pendingAfterSave = true
      return false
    }
    saveInFlight = true
    status.value = 'saving'
    errorMessage.value = ''
    try {
      const ok = await saveFn()
      if (ok) {
        markSaved()
        return true
      }
      status.value = 'error'
      if (!errorMessage.value) errorMessage.value = 'Speichern fehlgeschlagen.'
      return false
    } catch (e: unknown) {
      status.value = 'error'
      errorMessage.value = e instanceof Error ? e.message : 'Speichern fehlgeschlagen.'
      return false
    } finally {
      saveInFlight = false
      if (pendingAfterSave) {
        pendingAfterSave = false
        if (isDirty.value) scheduleSave()
      }
    }
  }

  function scheduleSave() {
    clearDebounce()
    if (!isEnabled() || !isDirty.value || saveInFlight) return
    const validationErr = validationMessage()
    if (validationErr) {
      status.value = 'dirty'
      errorMessage.value = validationErr
      return
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      void runSave()
    }, debounceMs)
  }

  function onWatchChange() {
    if (!isEnabled()) return
    if (!savedSnapshot.value) return
    if (isDirty.value) {
      status.value = 'dirty'
      scheduleSave()
    } else if (status.value === 'dirty') {
      status.value = 'saved'
      clearDebounce()
    }
  }

  async function flush(): Promise<boolean> {
    clearDebounce()
    if (!isDirty.value) return true
    return runSave()
  }

  if (watchSource != null) {
    watch(watchSource, () => onWatchChange(), { deep: true })
  }

  watch(isDirty, (dirty, wasDirty) => {
    if (!isEnabled() || !savedSnapshot.value) return
    if (dirty && status.value !== 'saving' && status.value !== 'error') {
      status.value = 'dirty'
    } else if (!dirty && wasDirty && status.value === 'dirty') {
      status.value = 'saved'
    }
  })

  const enabledNow = computed(() => isEnabled())
  watch(enabledNow, (now, was) => {
    if (!now || was || !savedSnapshot.value || !isDirty.value) return
    if (status.value !== 'saving' && status.value !== 'error') {
      status.value = 'dirty'
    }
    scheduleSave()
  })

  onBeforeUnmount(() => {
    clearDebounce()
  })

  return {
    status,
    errorMessage,
    isDirty,
    markSaved,
    resetSnapshot,
    flush,
    scheduleSave,
    runSave,
    setError: (msg: string) => {
      status.value = 'error'
      errorMessage.value = msg || 'Speichern fehlgeschlagen.'
    },
  }
}

export interface AggregateSaveStatus {
  kind: 'idle' | 'dirty' | 'saving' | 'saved' | 'error'
  message?: string
}

type SiloStatusEntry = SaveStatus | DirtyAutosaveHandle | null | undefined

/** Map silo status refs to a single aggregate for EventSaveStatusBar */
export function aggregateSaveStatus(silos: Record<string, SiloStatusEntry>): AggregateSaveStatus {
  const entries = Object.values(silos || {}).filter(Boolean)
  if (entries.some((s) => s === 'saving')) return { kind: 'saving' }
  const errors = entries
    .filter((s): s is DirtyAutosaveHandle => typeof s === 'object' && s?.status?.value === 'error')
    .map((s) => s.errorMessage.value)
    .filter(Boolean)
  if (errors.length) return { kind: 'error', message: errors[0] }
  if (
    entries.some(
      (s) => s === 'dirty' || (typeof s === 'object' && s?.isDirty?.value),
    )
  ) {
    return { kind: 'dirty' }
  }
  if (entries.some((s) => s === 'saved')) return { kind: 'saved' }
  return { kind: 'idle' }
}
