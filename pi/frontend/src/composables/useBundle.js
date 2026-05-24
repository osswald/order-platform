import { computed } from 'vue'
import {
  bundle,
  busy,
  bundleReady,
  lastSyncAt,
  patchEventArticles,
  refreshBundle,
  selectedEventId,
  showToast,
  syncError,
} from '../store'

export function useBundle() {
  return {
    bundle: computed(() => bundle.value),
    busy: computed(() => busy.value),
    lastSyncAt: computed(() => lastSyncAt.value),
    syncError: computed(() => syncError.value),
    selectedEventId,
    refreshBundle,
    bundleReady,
    isBundleReady: computed(() => bundleReady()),
    showToast,
    patchEventArticles,
  }
}
