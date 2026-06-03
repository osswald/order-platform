import { ref, computed, watch, onBeforeUnmount } from 'vue'

const DEBOUNCE_MS = 800

function serializeSnapshot(getSnapshot) {
  try {
    return JSON.stringify(getSnapshot())
  } catch {
    return ''
  }
}

/**
 * Tracks dirty state and debounced auto-save for a single editable silo.
 * @param {object} options
 * @param {() => unknown} options.getSnapshot - Serializable snapshot of current state
 * @param {() => Promise<boolean>} options.saveFn - Persist; return true on success
 * @param {import('vue').Ref|import('vue').ComputedRef|() => unknown} [options.watchSource] - Triggers dirty check when changed
 * @param {boolean} [options.enabled] - Ref/computed or static; when false, no watch/autosave
 * @param {number} [options.debounceMs]
 * @param {() => string|null|undefined} [options.validate] - Return error message to block save (no API call)
 */
export function useDirtyAutosave({
  getSnapshot,
  saveFn,
  watchSource = null,
  enabled = true,
  debounceMs = DEBOUNCE_MS,
  validate = null,
}) {
  const savedSnapshot = ref('')
  const status = ref('idle')
  const errorMessage = ref('')
  let debounceTimer = null
  let saveInFlight = false
  let pendingAfterSave = false

  const isEnabled = () => {
    if (typeof enabled === 'function') return enabled()
    if (enabled && typeof enabled === 'object' && 'value' in enabled) return !!enabled.value
    return enabled !== false
  }

  const isDirty = computed(() => {
    if (!savedSnapshot.value) return false
    return serializeSnapshot(getSnapshot) !== savedSnapshot.value
  })

  function validationMessage() {
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

  async function runSave() {
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
    } catch (e) {
      status.value = 'error'
      errorMessage.value = e?.message || 'Speichern fehlgeschlagen.'
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
      runSave()
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

  async function flush() {
    clearDebounce()
    if (!isDirty.value) return true
    return runSave()
  }

  if (watchSource != null) {
    watch(
      watchSource,
      () => onWatchChange(),
      { deep: true },
    )
  }

  watch(isDirty, (dirty, wasDirty) => {
    if (!isEnabled() || !savedSnapshot.value) return
    if (dirty && status.value !== 'saving' && status.value !== 'error') {
      status.value = 'dirty'
    } else if (!dirty && wasDirty && status.value === 'dirty') {
      status.value = 'saved'
    }
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
    setError: (msg) => {
      status.value = 'error'
      errorMessage.value = msg || 'Speichern fehlgeschlagen.'
    },
  }
}

/** Map silo status refs to a single aggregate for EventSaveStatusBar */
export function aggregateSaveStatus(silos) {
  const entries = Object.values(silos || {}).filter(Boolean)
  if (entries.some((s) => s === 'saving')) return { kind: 'saving' }
  const errors = entries
    .filter((s) => typeof s === 'object' && s?.status === 'error')
    .map((s) => s.errorMessage)
    .filter(Boolean)
  if (errors.length) return { kind: 'error', message: errors[0] }
  if (entries.some((s) => s === 'dirty' || (typeof s === 'object' && s?.isDirty))) {
    return { kind: 'dirty' }
  }
  if (entries.some((s) => s === 'saved')) return { kind: 'saved' }
  return { kind: 'idle' }
}
