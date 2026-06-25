import { computed } from 'vue'
import {
  adminRequiresPin,
  adminUnlocked,
  clearAdminSession,
  setAdminUnlocked,
  verifyAdminPin,
} from '@/store'

export function useAdminSession() {
  return {
    adminUnlocked: computed(() => adminUnlocked.value),
    requiresPin: computed(() => adminRequiresPin()),
    setAdminUnlocked,
    clearAdminSession,
    verifyAdminPin,
  }
}
