import { ref, unref, computed, watch } from 'vue'
import { apiFetch } from '../api'
import { useDirtyAutosave } from './useDirtyAutosave'

export function defaultReceiptProfile(kind = 'station') {
  return {
    logo_enabled: true,
    show_event_title: true,
    size_table_or_pickup: kind === 'customer' ? 'xlarge' : 'large',
    size_order_lines: 'normal',
    show_price: false,
    bottom_line: '',
  }
}

export function defaultPaymentReceiptProfile() {
  return {
    logo_enabled: true,
    show_event_title: true,
    size_order_lines: 'normal',
    bottom_line: '',
  }
}

export function defaultReceiptConfig(isEvent = false) {
  const cfg = {
    station_receipt: defaultReceiptProfile('station'),
    customer_receipt: defaultReceiptProfile('customer'),
    payment_receipt: defaultPaymentReceiptProfile(),
  }
  if (isEvent) {
    cfg.label_event_title = ''
  }
  return cfg
}

export function useReceiptPrinting(apiBasePathRef, { isEvent = false, autosave = false } = {}) {
  const basePath = () => unref(apiBasePathRef)
  const loading = ref(false)
  const saving = ref(false)
  const logoBusy = ref(false)
  const loadError = ref('')
  const saveMessage = ref('')
  const hasReceiptLogo = ref(false)
  const logoPreviewUrl = ref('')
  const config = ref(defaultReceiptConfig(isEvent))

  function mergeConfig(serverConfig) {
    const base = defaultReceiptConfig(isEvent)
    const merged = { ...base, ...serverConfig }
    merged.station_receipt = { ...base.station_receipt, ...(serverConfig?.station_receipt || {}) }
    merged.customer_receipt = { ...base.customer_receipt, ...(serverConfig?.customer_receipt || {}) }
    merged.payment_receipt = { ...base.payment_receipt, ...(serverConfig?.payment_receipt || {}) }
    if (isEvent) {
      merged.label_event_title = serverConfig?.label_event_title ?? ''
    }
    return merged
  }

  async function refreshLogoPreview() {
    if (logoPreviewUrl.value) {
      URL.revokeObjectURL(logoPreviewUrl.value)
      logoPreviewUrl.value = ''
    }
    const apiBasePath = basePath()
    if (!hasReceiptLogo.value || !apiBasePath) return
    try {
      const res = await apiFetch(`${apiBasePath}/receipt-logo`)
      if (!res.ok) return
      const blob = await res.blob()
      logoPreviewUrl.value = URL.createObjectURL(blob)
    } catch {
      /* ignore preview errors */
    }
  }

  async function load() {
    const apiBasePath = basePath()
    if (!apiBasePath) return
    loading.value = true
    loadError.value = ''
    try {
      const res = await apiFetch(`${apiBasePath}/receipt-printing`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Beleg-Einstellungen konnten nicht geladen werden')
      }
      const data = await res.json()
      config.value = mergeConfig(data.config || {})
      hasReceiptLogo.value = Boolean(data.has_receipt_logo)
      await refreshLogoPreview()
    } catch (e) {
      loadError.value = e.message || 'Laden fehlgeschlagen'
    } finally {
      loading.value = false
    }
  }

  async function save({ silent = false } = {}) {
    const apiBasePath = basePath()
    if (!apiBasePath) return false
    saving.value = true
    if (!silent) saveMessage.value = ''
    try {
      const res = await apiFetch(`${apiBasePath}/receipt-printing`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: config.value }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Speichern fehlgeschlagen')
      }
      const data = await res.json()
      config.value = mergeConfig(data.config || {})
      hasReceiptLogo.value = Boolean(data.has_receipt_logo)
      if (!silent) saveMessage.value = 'Beleg-Einstellungen gespeichert.'
      return true
    } catch (e) {
      const msg = e.message || 'Speichern fehlgeschlagen'
      if (!silent) saveMessage.value = msg
      throw e
    } finally {
      saving.value = false
    }
  }

  const autosaveEnabled = computed(() => autosave && !!basePath() && !loading.value)

  let dirtyAutosave = null
  if (autosave) {
    dirtyAutosave = useDirtyAutosave({
      getSnapshot: () => config.value,
      saveFn: async () => {
        try {
          return await save({ silent: true })
        } catch (e) {
          dirtyAutosave.setError(e.message || 'Speichern fehlgeschlagen')
          return false
        }
      },
      watchSource: config,
      enabled: autosaveEnabled,
    })
    watch(loading, (isLoading, wasLoading) => {
      if (wasLoading && !isLoading && !loadError.value) {
        dirtyAutosave.markSaved()
      }
    })
    watch(apiBasePathRef, () => {
      dirtyAutosave.resetSnapshot()
    })
  }

  async function uploadLogo(file) {
    const apiBasePath = basePath()
    if (!apiBasePath || !file) return
    logoBusy.value = true
    saveMessage.value = ''
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await apiFetch(`${apiBasePath}/receipt-logo`, { method: 'PUT', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Logo-Upload fehlgeschlagen')
      }
      hasReceiptLogo.value = true
      await refreshLogoPreview()
      saveMessage.value = 'Logo hochgeladen.'
    } catch (e) {
      saveMessage.value = e.message || 'Logo-Upload fehlgeschlagen'
    } finally {
      logoBusy.value = false
    }
  }

  async function removeLogo() {
    const apiBasePath = basePath()
    if (!apiBasePath) return
    logoBusy.value = true
    saveMessage.value = ''
    try {
      const res = await apiFetch(`${apiBasePath}/receipt-logo`, { method: 'DELETE' })
      if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Logo konnte nicht entfernt werden')
      }
      hasReceiptLogo.value = false
      if (logoPreviewUrl.value) {
        URL.revokeObjectURL(logoPreviewUrl.value)
        logoPreviewUrl.value = ''
      }
      saveMessage.value = 'Logo entfernt.'
    } catch (e) {
      saveMessage.value = e.message || 'Entfernen fehlgeschlagen'
    } finally {
      logoBusy.value = false
    }
  }

  return {
    loading,
    saving,
    logoBusy,
    loadError,
    saveMessage,
    hasReceiptLogo,
    logoPreviewUrl,
    config,
    load,
    save,
    uploadLogo,
    removeLogo,
    autosaveStatus: dirtyAutosave?.status,
    autosaveError: dirtyAutosave?.errorMessage,
    flushAutosave: dirtyAutosave?.flush,
  }
}
