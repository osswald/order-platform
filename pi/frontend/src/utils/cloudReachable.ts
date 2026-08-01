import { api } from '@/api'
import type { CloudReachableResponse } from '@/types/api'

const CACHE_MS = 15_000
let cloudCache: { at: number; reachable: boolean; reason: string | null } = {
  at: 0,
  reachable: false,
  reason: null,
}

export async function checkCloudReachable(force = false): Promise<{
  reachable: boolean
  reason: string | null
}> {
  const now = Date.now()
  if (!force && now - cloudCache.at < CACHE_MS) {
    return { reachable: cloudCache.reachable, reason: cloudCache.reason }
  }
  try {
    const res = await api<CloudReachableResponse>('/v1/cloud/reachable')
    cloudCache = {
      at: now,
      reachable: Boolean(res?.reachable),
      reason: res?.reason || null,
    }
  } catch {
    cloudCache = { at: now, reachable: false, reason: 'probe_failed' }
  }
  return { reachable: cloudCache.reachable, reason: cloudCache.reason }
}
